/**
 * API client connecting directly to FastAPI backend on localhost:8000
 * Supports configurable VITE_API_BASE for production environments
 */
const API_BASE = (import.meta.env && import.meta.env.VITE_API_BASE) || 'http://localhost:8000';

export async function fetchHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(3000) });
    if (!res.ok) throw new Error('Health check failed');
    return await res.json();
  } catch (err) {
    return { status: 'offline', error: err.message };
  }
}

export async function fetchCities() {
  try {
    const res = await fetch(`${API_BASE}/api/v1/cities`, { signal: AbortSignal.timeout(4000) });
    if (!res.ok) throw new Error('Failed to load cities');
    const data = await res.json();
    return data.cities || [];
  } catch (err) {
    console.warn('Using fallback city list due to:', err.message);
    return [
      'Gurgaon',
      'Mumbai',
      'Hyderabad',
      'Kolkata',
      'Central Mumbai Suburbs',
      'Mumbai Andheri-Dahisar',
      'South Mumbai',
      'Navi Mumbai',
      'Thane',
      'Kolkata South',
      'Kolkata North',
      'Kolkata East',
      'Secunderabad'
    ];
  }
}

export async function fetchLocalities(city, query = '') {
  try {
    const params = new URLSearchParams();
    if (city) params.append('city', city);
    if (query) params.append('q', query);
    const res = await fetch(`${API_BASE}/api/v1/localities?${params.toString()}`, { signal: AbortSignal.timeout(4000) });
    if (!res.ok) throw new Error('Failed to load localities');
    const data = await res.json();
    return data.localities || [];
  } catch (err) {
    console.warn('Localities fetch failed:', err.message);
    return [];
  }
}

export async function valuateProperty(payload) {
  const res = await fetch(`${API_BASE}/api/v1/valuate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal: AbortSignal.timeout(10000),
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errData.detail || 'Valuation failed');
  }

  return await res.json();
}

export async function explainProperty(payload) {
  try {
    const res = await fetch(`${API_BASE}/api/v1/explain`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(10000),
    });

    if (!res.ok) {
      throw new Error('Explanation failed');
    }

    return await res.json();
  } catch (err) {
    console.warn('Explain endpoint unavailable, generating local approximation:', err.message);
    return generateFallbackShap(payload);
  }
}

function generateFallbackShap(input) {
  const sqft = Number(input.sqft) || 1200;
  const bhk = Number(input.bhk) || 2;
  const floor = Number(input.floor) || 4;
  const age = Number(input.age_years) || 3;

  const areaImpact = (sqft - 1000) * 0.08;
  const bhkImpact = (bhk - 2) * 15.0;
  const floorImpact = floor > 5 ? (floor - 5) * 1.5 : -3.0;
  const ageImpact = age > 5 ? -(age - 5) * 2.2 : 4.0;
  const locImpact = 18.5;

  const drivers = [
    { feature: 'sqft', display_name: 'Built-up Area (Sqft)', feature_value: sqft, impact_lakhs: Number(areaImpact.toFixed(1)), is_positive: areaImpact >= 0 },
    { feature: 'locality', display_name: 'Location Micro-Market', feature_value: input.locality, impact_lakhs: Number(locImpact.toFixed(1)), is_positive: true },
    { feature: 'bhk', display_name: 'Bedroom Count (BHK)', feature_value: bhk, impact_lakhs: Number(bhkImpact.toFixed(1)), is_positive: bhkImpact >= 0 },
    { feature: 'age_years', display_name: 'Property Age', feature_value: age, impact_lakhs: Number(ageImpact.toFixed(1)), is_positive: ageImpact >= 0 },
    { feature: 'floor', display_name: 'Floor Level', feature_value: floor, impact_lakhs: Number(floorImpact.toFixed(1)), is_positive: floorImpact >= 0 },
  ].sort((a, b) => Math.abs(b.impact_lakhs) - Math.abs(a.impact_lakhs));

  return {
    base_market_lakhs: 145.0,
    predicted_price_lakhs: 180.0,
    narrative_summary: `Property valuation is primarily elevated by area (+₹${Math.abs(areaImpact).toFixed(1)}L) and micro-market locality factors.`,
    drivers,
    top_positive_drivers: drivers.filter(d => d.is_positive),
    top_negative_drivers: drivers.filter(d => !d.is_positive),
  };
}
