"""
Script to create a smart meter dashboard with cyber design
"""

# Read the cyber dashboard template
with open('dashboard/cyber_dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the title
content = content.replace(
    '<title>Smart Grid Monitor</title>',
    '<title>Smart Meters - Enhanced Detection Monitor</title>'
)

# Replace the header title
content = content.replace(
    '⚡ SMART GRID MONITOR<span>SYSTEME ELECTRIQUE INTELLIGENT - TEMPS REEL</span>',
    '🔋 SMART METERS MONITOR<span>DETECTION AMELIOREE - 100 COMPTEURS INTELLIGENTS</span>'
)

# Find and replace the JavaScript section at the end
# We'll inject our smart meter data fetching code

js_injection = '''
<script>
// Smart Meter Dashboard - Real Data from Enhanced Detection
const API_BASE = '';
let refreshCount = 0;
let smartMeterData = null;

// Update clock
function updateClock() {
  const now = new Date();
  document.getElementById('clock').textContent = now.toLocaleTimeString();
  document.getElementById('datestamp').textContent = now.toLocaleDateString('en-US', {
    weekday: 'short', year: 'numeric', month: 'short', day: 'numeric'
  });
}

// Fetch smart meter data
async function fetchSmartMeterData() {
  try {
    const response = await fetch(`${API_BASE}/api/smart-meters/status?limit=20`);
    if (!response.ok) throw new Error('API Error');
    
    smartMeterData = await response.json();
    updateDashboard(smartMeterData);
    
    document.getElementById('dot-api').className = 'status-dot online';
    refreshCount++;
    document.getElementById('refresh-count').textContent = refreshCount;
  } catch (error) {
    console.error('Error fetching smart meter data:', error);
    document.getElementById('dot-api').className = 'status-dot offline';
  }
}

// Update dashboard with smart meter data
function updateDashboard(data) {
  if (!data || !data.summary) return;
  
  const summary = data.summary;
  const latest = data.latest_reading || {};
  
  // Update KPIs
  document.getElementById('kpi-prod').textContent = summary.total_readings.toLocaleString();
  document.getElementById('kpi-conso').textContent = summary.total_alerts.toLocaleString();
  document.getElementById('kpi-balance').textContent = `${summary.alert_rate.toFixed(2)}%`;
  document.getElementById('kpi-batt').textContent = '100';
  
  // Update labels
  document.querySelector('#kpi-prod').parentElement.querySelector('.kpi-label').textContent = 'TOTAL READINGS';
  document.querySelector('#kpi-conso').parentElement.querySelector('.kpi-label').textContent = 'TOTAL ALERTS';
  document.querySelector('#kpi-balance').parentElement.querySelector('.kpi-label').textContent = 'ALERT RATE';
  document.querySelector('#kpi-batt').parentElement.querySelector('.kpi-label').textContent = 'ACTIVE METERS';
  
  // Update meter type distribution
  if (summary.meter_types) {
    const types = summary.meter_types;
    const residential = types.residentiel || 0;
    const commercial = types.commercial || 0;
    const industrial = types.industriel || 0;
    const total = residential + commercial + industrial;
    
    if (total > 0) {
      document.getElementById('solar-pct-text').textContent = `${Math.round(residential/total*100)}%`;
      document.getElementById('wind-pct-text').textContent = `${Math.round(commercial/total*100)}%`;
      document.getElementById('coal-pct-text').textContent = `${Math.round(industrial/total*100)}%`;
      
      document.getElementById('solar-w').textContent = `${residential}`;
      document.getElementById('wind-w').textContent = `${commercial}`;
      document.getElementById('coal-w').textContent = `${industrial}`;
      
      // Update gauge arcs
      const solarOffset = 173 - (173 * residential / total);
      const windOffset = 173 - (173 * commercial / total);
      const coalOffset = 173 - (173 * industrial / total);
      
      document.getElementById('solar-arc').style.strokeDashoffset = solarOffset;
      document.getElementById('wind-arc').style.strokeDashoffset = windOffset;
      document.getElementById('coal-arc').style.strokeDashoffset = coalOffset;
    }
    
    // Update labels
    document.querySelector('.gauge-label').textContent = 'RESIDENTIAL';
    document.querySelectorAll('.gauge-label')[1].textContent = 'COMMERCIAL';
    document.querySelectorAll('.gauge-label')[2].textContent = 'INDUSTRIAL';
  }
  
  // Update status counts
  if (summary.status_counts) {
    const normal = summary.status_counts.NORMAL || 0;
    const alert = summary.status_counts.ALERTE || 0;
    const total = normal + alert;
    
    if (total > 0) {
      const normalPct = Math.round(normal / total * 100);
      const alertPct = Math.round(alert / total * 100);
      
      document.getElementById('batt-total-pct').textContent = `${normalPct}%`;
      document.getElementById('batt-cap').textContent = `${alertPct}%`;
      document.getElementById('batt-temp').textContent = `${total}`;
      
      document.getElementById('batt-total-pct').parentElement.querySelector('div:last-child').textContent = 'NORMAL';
      document.getElementById('batt-cap').parentElement.querySelector('div:last-child').textContent = 'ALERTS';
      document.getElementById('batt-temp').parentElement.querySelector('div:last-child').textContent = 'TOTAL';
    }
  }
  
  // Update latest reading info
  if (latest.timestamp) {
    document.getElementById('eff-pct').textContent = `${latest.consommation_kw.toFixed(2)} kW`;
    const effBar = (latest.tension_v - 207) / (253 - 207) * 100;
    document.getElementById('eff-bar').style.width = `${Math.max(0, Math.min(100, effBar))}%`;
  }
}

// Initialize
updateClock();
setInterval(updateClock, 1000);
fetchSmartMeterData();
setInterval(fetchSmartMeterData, 3000);

// Dummy functions for compatibility
function closeBusTooltip() {}
</script>
</body>
</html>
'''

# Find the closing </body> tag and replace everything after the last script
end_pos = content.rfind('</body>')
if end_pos > 0:
    # Find the last <script> tag before </body>
    last_script_start = content.rfind('<script>', 0, end_pos)
    if last_script_start > 0:
        # Replace from last script to end
        content = content[:last_script_start] + js_injection
    else:
        # Just append before </body>
        content = content[:end_pos] + js_injection

# Write the new dashboard
with open('dashboard/smart_meters_cyber.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Smart meter dashboard created successfully!")
print("📍 Location: dashboard/smart_meters_cyber.html")
print("🌐 URL: http://127.0.0.1:8000/blockchain-dashboard")
