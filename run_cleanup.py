
def clean_console():
    filepath = 'apps/dashboard/console.html'
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Step 1: Remove deep CSS
        css_start_idx = content.find("/* \n         ==================================================\n         * GIGAFIELD ENTERPRISE DEEP METRICS ENGINE CSS")
        if css_start_idx != -1:
            css_end_idx = content.find("</style>", css_start_idx)
            if css_end_idx != -1:
                content = content[:css_start_idx] + "\n    " + content[css_end_idx:]

        # Step 2: Remove the payload replacing #view-topology
        topo_start_idx = content.find("<div id='view-topology' class='view-section'")
        if topo_start_idx != -1:
            main_end_idx = content.find("</main>", topo_start_idx)
            if main_end_idx != -1:
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
                content = content[:topo_start_idx] + orig_topo + content[main_end_idx:]

        # Step 3: Remove telemetry manifest
        manifest_idx = content.find("<!-- DEEP SYSTEM TELEMETRY MANIFEST & CAUSAL NODE LOGS -->")
        if manifest_idx != -1:
            content = content[:manifest_idx] + "</body>\n</html>"

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print("clean_console: SUCCESS")

    except Exception as e:
        print(f"clean_console: FAIL -> {e}")

def clean_index():
    filepath = 'apps/dashboard/index.html'
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Step 1: Remove deep CSS
        css_start_idx = content.find("/* \n         ==================================================\n         * GIGAFIELD ENTERPRISE DEEP METRICS ENGINE CSS")
        if css_start_idx != -1:
            css_end_idx = content.find("</style>", css_start_idx)
            if css_end_idx != -1:
                content = content[:css_start_idx] + "\n    " + content[css_end_idx:]

        # Step 2: Remove <section class="deep-analytics-grid">
        grid_start_idx = content.find('<section class="deep-analytics-grid"')
        if grid_start_idx != -1:
            # We want to replace everything up to <footer> with the original section
            footer_idx = content.find('<footer>', grid_start_idx)
            if footer_idx != -1:
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
                content = content[:grid_start_idx] + orig_preview + content[footer_idx:]

        # Step 3: Remove manifest & docs
        manifest_idx = content.find("<!-- DEEP SYSTEM TELEMETRY MANIFEST & CAUSAL NODE LOGS -->")
        if manifest_idx != -1:
            content = content[:manifest_idx] + "</body>\n</html>"

        docs_idx = content.find("<!-- EXTENDED DATA ARCHITECTURE & FAQ SECTION -->")
        if docs_idx != -1:
            content = content[:docs_idx] + "</body>\n</html>"

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print("clean_index: SUCCESS")

    except Exception as e:
        print(f"clean_index: FAIL -> {e}")


clean_console()
clean_index()
