import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
from sklearn.dummy import DummyRegressor
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

from backend import features as f, prepare_data as p

BASE = Path(__file__).resolve().parent
EXPECTED = ['sqft', 'bhk', 'floor', 'age_years', 'lat', 'lon', 'osm_schools_2km',
            'osm_hospitals_2km', 'osm_metro_dist_km', 'sqft_per_bhk', 'is_high_floor', 'amenity_index']


def training_fixture():
    rows = []
    for i in range(8):
        context = ([18.5, 73.8, 4, 2, 1, i * 2, i * 2] if i < 6 else
                   [19, 74, 8, 4, 3, 20, 20] if i == 6 else [19.1, 72.9, 10, 6, 5, 30, 30])
        rows.append(dict(row_id=f'r{i}', city='Pune' if i < 7 else 'Mumbai',
                         locality='Alpha Park' if i < 6 else 'Beta' if i == 6 else 'Gamma',
                         sqft=900 + i * 100, bhk=2, price_lakhs=(10000 + i * 100) * (900 + i * 100) / 100000,
                         price_per_sqft=10000 + i * 100, **dict(zip(f.CONTEXT_COLS, context))))
    return pd.DataFrame(rows, index=[91, 3, 82, 7, 64, 18, 45, 2])


class ParserTests(unittest.TestCase):
    def test_prices(self):
        for value, expected in [('₹ 1.25 Cr', 125), ('Rs. 75 Lac', 75), ('INR 80 L', 80),
                                ('2 crores', 200), ('50 lakhs', 50), ('₹ 75,00,000', 75),
                                (7500000, 75), ('95', 95), ('1-2 Cr', 150),
                                ('80 Lac - 1.2 Cr', 100), ('50 to 70 L', 60)]:
            with self.subTest(value=value):
                self.assertAlmostEqual(p.parse_price(value), expected)
        self.assertAlmostEqual(p.parse_price(5000, numeric_rupees=True), .05)
        for value in [0, '0 Cr', None, '', np.nan, 'Price on request', '-50', '80 per sqft', '500/month',
                      '₹ -50 Lac', 'INR -5000000', 'Rs. -50 L']:
            with self.subTest(invalid_price=value):
                self.assertTrue(np.isnan(p.parse_price(value)), 'Invalid prices must not become positive')

    def test_area_age_and_floor(self):
        for value, expected in [('1,200 sq.ft.', 1200), ('1200 square feet', 1200),
                                ('100 sq m', 1076.39104167), ('100 m²', 1076.39104167),
                                ('100 sq yd', 900), ('2 acres', 87120), ('1 hectare', 107639.104167)]:
            with self.subTest(area=value):
                self.assertAlmostEqual(p.parse_area(value), expected)
        self.assertEqual(p.parse_area(100, numeric_factor=9), 900)
        self.assertEqual(p.parse_area('100 sqft', numeric_factor=9), 100)
        for code, age in [(1, 3), (2, 7.5), (3, 15), (5, 0), (6, .5)]:
            for value in [code, str(code), f'{code}.0']:
                with self.subTest(age=value):
                    self.assertEqual(p.parse_age(value), age)
        for value in [0, '0', '4', '99', None, '', np.nan]:
            with self.subTest(unknown_age=value):
                self.assertTrue(np.isnan(p.parse_age(value)))
        self.assertEqual(p.parse_age('5-10 years'), 7.5)
        for value, expected in [('G', 0), ('GF', 0), ('Ground floor', 0), ('B', -1),
                                ('L', -1), ('LG', -1), ('Lower Ground', -1), ('7 of 20', 7), ('-2', -2)]:
            with self.subTest(floor=value):
                self.assertEqual(p.parse_floor(value), expected)
        for parser, values in [(p.parse_area, [0, '-10', None, '', np.nan]),
                               (p.parse_floor, [None, 'unknown', '-6', '151'])]:
            for value in values:
                with self.subTest(parser=parser.__name__, value=value):
                    self.assertTrue(np.isnan(parser(value)))

    def test_coordinates_and_safe_structured_parsing(self):
        for value in [{'LATITUDE': 18.5, 'LONGITUDE': 73.8},
                      '{"latitude": 18.5, "longitude": 73.8}',
                      "{'LATITUDE': '73.8', 'LONGITUDE': '18.5'}"]:
            self.assertEqual(p.parse_coordinates(value), (18.5, 73.8))
        with patch('os.system') as system:
            for value in [None, '', 'not JSON', '[]', '{"lat": 18.5}',
                          '{"LATITUDE": 99, "LONGITUDE": 999}',
                          '{"LATITUDE": "nan", "LONGITUDE": 73.8}',
                          "__import__('os').system('must-not-execute')", 'x' * 100001]:
                with self.subTest(value=str(value)[:80]):
                    self.assertTrue(np.isnan(p.parse_coordinates(value)).all())
            system.assert_not_called()

    def test_landmarks(self):
        entries = [{'category': 'Education', 'text': '3 schools'},
                   {'category': 'Health', 'text': '2 hospitals'},
                   {'category': 'Connectivity', 'text': '3 metro stations'}]
        self.assertEqual(p.parse_landmarks(json.dumps(entries), None), (3, 2, 1))
        self.assertEqual(p.parse_landmarks({'category': 'school'}, 100), (1, 0, 5))
        self.assertEqual(p.parse_landmarks('', 100), (15, 8, 4 / 7))
        for total in [None, '', np.nan, 'unknown', -1]:
            with self.subTest(total=total):
                self.assertEqual(p.parse_landmarks(None, total), (0, 0, 5))


class FeatureTests(unittest.TestCase):
    def setUp(self):
        self.train = training_fixture()
        self.lookup = f.build_locality_lookup(self.train)
        self.row = dict(city='  pUnE ', locality=' ALPHA   PARK ', sqft=900, bhk=3, floor=9)

    def test_feature_contract_and_case_insensitive_lookup(self):
        self.assertEqual(f.FEATURE_COLS, EXPECTED)
        rows = pd.DataFrame([self.row, dict(self.row, sqft=1200, bhk=2, floor=10)], index=[41, 7])
        original = rows.copy(deep=True)
        X = f.build_features(rows, self.lookup)
        self.assertEqual(list(X.columns), EXPECTED)
        pd.testing.assert_index_equal(X.index, rows.index)
        np.testing.assert_allclose(X[['sqft_per_bhk', 'is_high_floor', 'amenity_index']], [[300, 0, 8], [600, 1, 8]])
        np.testing.assert_allclose(X[['lat', 'lon']], [[18.5, 73.8]] * 2)
        inverted = pd.DataFrame([dict(self.row, lat=73.8, lon=18.5)])
        np.testing.assert_allclose(f.build_features(inverted, self.lookup)[['lat', 'lon']], [[18.5, 73.8]])
        pd.testing.assert_frame_equal(rows, original)

    def test_train_only_imputation_and_indices(self):
        train = self.train.copy()
        train.loc[91, ['lat', 'lon', 'floor', 'age_years']] = np.nan
        test = pd.DataFrame([dict(self.row, locality='Unseen', floor=np.nan),
                             dict(self.row, city='Unknown', floor=np.nan)], index=[200, 100])
        test['age_years'] = np.nan
        test['price_per_sqft'], test['price_lakhs'] = [1e12, -1e12], [1e10, -1e10]
        original_train, original_test = train.copy(), test.copy()
        trained, tested, lookup = p.impute_split(train, test)
        pd.testing.assert_index_equal(trained.index, train.index)
        pd.testing.assert_index_equal(tested.index, test.index)
        np.testing.assert_allclose(tested[f.CONTEXT_COLS[:5]], [[18.75, 73.9, 6, 3, 2], [19, 73.8, 8, 4, 3]])
        np.testing.assert_allclose(tested[['floor', 'age_years']], train['floor'].median())
        self.assertEqual(trained.loc[91, 'lat'], 18.5)
        changed = test.assign(price_per_sqft=7, price_lakhs=8)
        trained2, _, lookup2 = p.impute_split(train, changed)
        for actual, expected in [(trained, trained2), (lookup, lookup2), (train, original_train), (test, original_test)]:
            pd.testing.assert_frame_equal(actual, expected)
        pd.testing.assert_frame_equal(f.build_features(test, lookup), f.build_features(changed, lookup))

    def test_invalid_features_and_lookup(self):
        for column, values in {'sqft': [299, 10001, 0, None, np.inf, 'bad'],
                               'bhk': [0, 11, None, np.nan, 'bad']}.items():
            for value in values:
                with self.subTest(column=column, value=value), self.assertRaises(ValueError):
                    f.build_features(pd.DataFrame([dict(self.row, **{column: value})]), self.lookup)
        for lookup in [self.lookup.iloc[:0], pd.concat([self.lookup, self.lookup])]:
            with self.assertRaises(ValueError):
                f.build_features(pd.DataFrame([self.row]), lookup)

    def test_intervals_support_and_haversine(self):
        low, high = f.ordered_interval(np.array([100, 100, 100]), [120, 50, 120], [80, 80, 150])
        np.testing.assert_equal(low, [80, 50, 100])
        np.testing.assert_equal(high, [120, 100, 150])
        np.testing.assert_equal(f.auto_accept_mask([100] * 4, [80, 80, 79, 95], [120, 120, 121, 105], [5, 4, 5, 0]),
                                [True, False, False, False])
        np.testing.assert_allclose(f.haversine_km(0, 0, [0, 0, 0], [0, 1, 180]),
                                   [0, 111.19508, 20015.11444], atol=1e-5)
        self.assertAlmostEqual(float(f.haversine_km(19.0760, 72.8777, 28.6139, 77.2090)), 1148.1, delta=1)

    def test_synthetic_prediction(self):
        X = f.build_features(self.train, self.lookup)
        scaler = StandardScaler().fit(X)
        bundle = dict(localities_lookup=self.lookup, comparables=self.train, scaler=scaler,
                      nn=NearestNeighbors().fit(scaler.transform(X)), model_version='unit-test',
                      feature_cols=EXPECTED, target_transform='log')
        for name, price in [('model_point', 100), ('model_low', 110), ('model_high', 90)]:
            bundle[name] = DummyRegressor(strategy='constant', constant=np.log(price)).fit(X, np.zeros(len(X)))
        result = f.predict_valuation(dict(self.row, row_id='r0'), bundle)
        json.dumps(result, allow_nan=False)
        self.assertEqual([result[k] for k in ['price_lakhs', 'range_low_lakhs', 'range_high_lakhs']], [100, 90, 110])
        self.assertTrue(result['auto_accept'])
        ids = [item['row_id'] for item in result['comparables']]
        self.assertEqual(len(set(ids)), 3)
        self.assertTrue(set(ids) <= {f'r{i}' for i in range(1, 7)})
        self.assertFalse(f.predict_valuation(dict(self.row, locality='Unseen'), bundle)['auto_accept'])
        with self.assertRaises(ValueError):
            f.predict_valuation(dict(self.row, city='Unsupported'), bundle)


class ArtifactTests(unittest.TestCase):
    def artifact(self, relative):
        path = BASE / relative
        if not path.is_file():
            self.skipTest(f'Artifact absent: {path}')
        return path

    def csv(self, name):
        return pd.read_csv(self.artifact(f'data/processed/{name}.csv'))

    def bundle(self):
        import joblib
        return joblib.load(self.artifact('models/valuation_bundle.pkl'))

    def test_splits_lookup_and_features(self):
        for split in ['random', 'locality_heldout']:
            with self.subTest(split=split):
                train, test = self.csv(f'train_{split}'), self.csv(f'test_{split}')
                self.assertTrue(len(train) and len(test))
                self.assertFalse(set(train.row_id) & set(test.row_id))
                self.assertTrue(train.row_id.is_unique and test.row_id.is_unique)
                if split == 'locality_heldout':
                    self.assertFalse(set(f.normalize_key(train.locality)) & set(f.normalize_key(test.locality)))
                lookup = f.build_locality_lookup(train)
                if split == 'random':
                    pd.testing.assert_frame_equal(self.csv('localities_lookup'), lookup, check_dtype=False, rtol=1e-7)
                for frame in [train, test]:
                    X = f.build_features(frame, lookup)
                    self.assertEqual(list(X.columns), EXPECTED)
                    self.assertTrue(np.isfinite(X.to_numpy()).all())
                    pd.testing.assert_frame_equal(X, f.build_features(frame.assign(price_lakhs=1e12, price_per_sqft=-1e12), lookup))

    def test_bundle_reload_prediction_and_comparables(self):
        bundle = self.bundle()
        required = {'model_point', 'model_low', 'model_high', 'scaler', 'nn', 'comparables',
                    'localities_lookup', 'feature_cols', 'model_version', 'target_transform'}
        self.assertTrue(required <= bundle.keys())
        self.assertEqual(bundle['feature_cols'], EXPECTED)
        self.assertEqual(bundle['target_transform'], 'log')
        train = self.csv('train_random')
        pd.testing.assert_frame_equal(bundle['localities_lookup'], f.build_locality_lookup(train), check_dtype=False, rtol=1e-7)
        self.assertTrue(set(bundle['comparables'].row_id) <= set(train.row_id))
        eligible = train[f.normalize_key(train.city).map(f.normalize_key(train.city).value_counts()) >= 4]
        self.assertFalse(eligible.empty)
        for row in eligible.groupby('city').head(1).to_dict('records'):
            result = f.predict_valuation(row, bundle)
            json.dumps(result, allow_nan=False)
            self.assertEqual(result, f.predict_valuation(row, self.bundle()))
            self.assertTrue(0 < result['range_low_lakhs'] <= result['price_lakhs'] <= result['range_high_lakhs'])
            self.assertIsInstance(result['auto_accept'], bool)
            comps = result['comparables']
            self.assertEqual(len(comps), 3)
            self.assertEqual(len({c['row_id'] for c in comps}), 3)
            self.assertNotIn(row['row_id'], {c['row_id'] for c in comps})
            self.assertTrue({c['row_id'] for c in comps} <= set(train.row_id))
            self.assertTrue(all(c['city'].strip().lower() == row['city'].strip().lower() for c in comps))

    def test_evaluation_metrics_match_artifacts(self):
        metrics = json.loads(self.artifact('data/processed/evaluation_metrics.json').read_text())
        json.dumps(metrics, allow_nan=False)
        self.assertEqual(metrics['model_version'], self.bundle()['model_version'])
        for split in ['random', 'locality_heldout']:
            for kind in ['train', 'test']:
                self.assertEqual(metrics['splits'][split][f'{kind}_rows'], len(self.csv(f'{kind}_{split}')))

    def test_shap_log_additivity(self):
        bundle = self.bundle()
        if importlib.util.find_spec('shap') is None:
            self.skipTest('SHAP is not installed')
        import shap
        X = f.build_features(bundle['comparables'].head(3), bundle['localities_lookup'])
        explanation = shap.TreeExplainer(bundle['model_point'])(X)
        np.testing.assert_allclose(explanation.base_values + explanation.values.sum(axis=1),
                                   bundle['model_point'].predict(X), rtol=1e-5, atol=1e-5)
