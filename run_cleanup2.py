import os

dashboard_path = 'apps/dashboard/console.html'
index_path = 'apps/dashboard/index.html'

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

console = read_file(dashboard_path)
start_topo = console.find("<div id='view-topology' class='view-section'")
if start_topo != -1:
    end_topo = console.find('</main>', start_topo)
    if end_topo != -1:
        orig_topo = '''        <div id="view-topology" class="view-section"
            style="display: none; grid-column: 1 / span 2; justify-content: center; align-items: center; text-align: center;">
            <div class="panel" style="padding: 60px; max-width: 600px;">
                <i data-lucide="network"
                    style="width: 64px; height: 64px; color: var(--accent-glow); margin-bottom: 20px;"></i>
                <h2 style="font-family: 'Outfit'; margin-bottom: 10px;">Global Network Topology</h2>
                <p style="color: var(--text-secondary);">Mapping interconnected asset nodes across SA_EAST and
                    EMEA
                    regions. Real-time reachability matrix loading...</p>
            </div>
        </div>\n    '''
        console = console[:start_topo] + orig_topo + console[end_topo:]
write_file(dashboard_path, console)

index = read_file(index_path)
start_grid = index.find('<section class="deep-analytics-grid"')
if start_grid != -1:
    end_grid = index.find('<footer>', start_grid)
    if end_grid != -1:
        orig_preview = '''    <section class="preview-section">
        <div class="feature-card">
            <div class="status-badge">ACTIVE</div>
            <span class="feature-icon">🛰️</span>
            <h3>Atmospheric Ingestion</h3>
            <p>Direct CAMS & MODIS telemetry fusion. Sub-0.5ms processing latency for 72-hour AOD forecasting.</p>
        </div>
        <div class="feature-card">
            <div class="status-badge">ACTIVE</div>
            <span class="feature-icon">🧬</span>
            <h3>Geotechnical Models</h3>
            <p>Physics-informed mineralogy profiling. Predicting Mohs-scale abrasion and Arrhenius thermal stress.</p>
        </div>
        <div class="feature-card">
            <div class="status-badge"
                style="background: rgba(240, 165, 0, 0.1); color: var(--amber); border-color: rgba(240, 165, 0, 0.2);">
                SCALED</div>
            <span class="feature-icon">📐</span>
            <h3>Causal Propagation</h3>
            <p>Matrix-based reachability analysis for interconnected asset chains. Automated root-cause isolation.</p>
        </div>
    </section>\n\n    '''
        index = index[:start_grid] + orig_preview + index[end_grid:]
write_file(index_path, index)
print('Restored Topo & Grid to original via script file.')
