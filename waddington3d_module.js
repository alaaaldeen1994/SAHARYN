// Insert this code right before SECTION 8 (before "const BiosimBridge")

/* =========================
   3D WADDINGTON'S LANDSCAPE MODULE
   ========================= */

/**
 * Waddington3D - Scientific 3D Epigenetic Landscape Visualization
 * Based on Yamanaka's Nobel Prize research (2012) and Waddington's concept (1957)
 */
const Waddington3D = {
    active: false,
    scene: null,
    camera: null,
    renderer: null,
    controls: null,
    landscapeMesh: null,
    cellMeshes: [],

    // Canvas reference
    canvas2d: null,
    canvas3d: null,

    init(canvas2d, canvas3d) {
        this.canvas2d = canvas2d;
        this.canvas3d = canvas3d;

        // Create Three.js scene
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x000000);
        this.scene.fog = new THREE.Fog(0x000000, 10, 50);

        // Create camera
        const aspect = canvas3d.clientWidth / canvas3d.clientHeight;
        this.camera = new THREE.PerspectiveCamera(50, aspect, 0.1, 100);
        this.camera.position.set(5, 8, 12);
        this.camera.lookAt(0, 0, 0);

        // Create renderer
        this.renderer = new THREE.WebGLRenderer({
            canvas: canvas3d,
            antialias: true,
            alpha: true
        });
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.renderer.setSize(canvas3d.clientWidth, canvas3d.clientHeight);
        this.renderer.shadowMap.enabled = true;

        // Add orbit controls
        this.controls = new THREE.OrbitControls(this.camera, canvas3d);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;
        this.controls.minDistance = 3;
        this.controls.maxDistance = 25;
        this.controls.maxPolarAngle = Math.PI / 2.1;

        // Add lights
        const ambientLight = new THREE.AmbientLight(0x404040, 1.5);
        this.scene.add(ambientLight);

        const mainLight = new THREE.DirectionalLight(0xffffff, 1.2);
        mainLight.position.set(5, 10, 5);
        mainLight.castShadow = true;
        this.scene.add(mainLight);

        const fillLight = new THREE.DirectionalLight(0x4488ff, 0.5);
        fillLight.position.set(-5, 3, -5);
        this.scene.add(fillLight);

        // Build the landscape
        this.buildLandscape();

        BiosimUI.notify('3D Engine', 'Waddington Landscape Initialized', 'suc');
    },

    buildLandscape() {
        // Create landscape geometry (grid-based surface)
        const resolution = 80;
        const size = 10;
        const geometry = new THREE.PlaneGeometry(size, size, resolution, resolution);

        // Calculate heights based on potential energy function
        const vertices = geometry.attributes.position.array;
        for (let i = 0; i < vertices.length; i += 3) {
            const x = vertices[i] / size + 0.5;     // Normalize to 0-1
            const y = vertices[i + 1] / size + 0.5;  // Normalize to 0-1
            const z = this.potentialEnergy(x, y);
            vertices[i + 2] = z * 2; // Scale height for visibility
        }
        geometry.computeVertexNormals();

        // Create material with vertex coloring based on height
        const material = new THREE.MeshStandardMaterial({
            color: 0x1a5490,
            metalness: 0.3,
            roughness: 0.7,
            wireframe: false,
            side: THREE.DoubleSide
        });

        this.landscapeMesh = new THREE.Mesh(geometry, material);
        this.landscapeMesh.rotation.x = -Math.PI / 2;
        this.landscapeMesh.receiveShadow = true;
        this.scene.add(this.landscapeMesh);

        // Add grid helper
        const gridHelper = new THREE.GridHelper(size, 20, 0x2563eb, 0x1f1f1f);
        gridHelper.position.y = -2;
        this.scene.add(gridHelper);

        // Add valley labels (text sprites would go here in full version)
    },

    potentialEnergy(x, y) {
        /**
         * Energy function creating Waddington's landscape
         * Valleys (minima) = stable cell states
         * Hills/ridges = transition barriers
         * 
         * Based on gene expression:
         * x = Pluripotency (OCT4, SOX2, NANOG)
         * y = Differentiation (NEURO, CARDIO)
         */

        // Valley definitions: {x, y, depth, width}
        const valleys = [
            { x: 0.8, y: 0.2, depth: 1.2, width: 0.15, name: 'IPSC' },      // iPSC valley
            { x: 0.2, y: 0.2, depth: 0.9, width: 0.18, name: 'SOMATIC' },  // Somatic valley
            { x: 0.5, y: 0.85, depth: 1.0, width: 0.12, name: 'NEURO' },   // Neuro valley
            { x: 0.15, y: 0.7, depth: 0.95, width: 0.12, name: 'CARDIO' }  // Cardio valley
        ];

        // Calculate energy as sum of Gaussian valleys
        let energy = 0.5; // Base elevation

        valleys.forEach(v => {
            const dx = x - v.x;
            const dy = y - v.y;
            const distSq = dx * dx + dy * dy;
            const valley = -v.depth * Math.exp(-distSq / (v.width * v.width));
            energy += valley;
        });

        // Add slight upward tilt for TUMOR region (unstable)
        const tumorPenalty = Math.max(0, (x - 0.7) * (y - 0.7)) * 0.8;
        energy += tumorPenalty;

        return energy;
    },

    updateCells(agents) {
        if (!this.active) return;

        // Remove old cell meshes
        this.cellMeshes.forEach(mesh => this.scene.remove(mesh));
        this.cellMeshes = [];

        // Create new cell meshes
        agents.forEach(agent => {
            if (agent.type === 'DEATH') return;

            // Map gene state to 3D position
            const s = agent.network.state;
            const xGene = (s[0] + s[4] + s[6] + 3) / 6;  // Pluripotency (0-1)
            const yGene = (s[1] + s[2] + 2) / 4;          // Differentiation (0-1)

            // Convert to world coordinates
            const worldX = (xGene - 0.5) * 10;
            const worldY = (yGene - 0.5) * 10;
            const worldZ = this.potentialEnergy(xGene, yGene) * 2 + 0.3;

            // Cell size based on type
            const sizeMap = {
                TUMOR: 0.25, IPSC: 0.18, NEURO: 0.16,
                CARDIO: 0.14, SOMATIC: 0.12
            };
            const radius = sizeMap[agent.type] || 0.12;

            // Cell color
            const colorMap = {
                SOMATIC: 0x64748b, IPSC: 0xeab308, NEURO: 0xa855f7,
                CARDIO: 0xf43f5e, TUMOR: 0xef4444
            };
            const color = colorMap[agent.type] || 0x888888;

            // Create cell sphere
            const geometry = new THREE.SphereGeometry(radius, 16, 16);
            const material = new THREE.MeshStandardMaterial({
                color: color,
                emissive: color,
                emissiveIntensity: 0.3,
                metalness: 0.2,
                roughness: 0.8
            });

            const cellMesh = new THREE.Mesh(geometry, material);
            cellMesh.position.set(worldX, worldZ, worldY);
            cellMesh.castShadow = true;

            this.scene.add(cellMesh);
            this.cellMeshes.push(cellMesh);
        });
    },

    toggle() {
        this.active = !this.active;

        if (this.active) {
            // Switch to 3D view
            this.canvas2d.style.display = 'none';
            this.canvas3d.style.display = 'block';

            // Initialize if needed
            if (!this.scene) {
                this.init(this.canvas2d, this.canvas3d);
            }

            // Update button style
            const btn = document.getElementById('3d-toggle-btn');
            if (btn) {
                btn.className = 'bg-blue-600 hover:bg-blue-700 text-[9px] text-white border border-blue-500 px-2 py-1 rounded backdrop-blur font-mono transition-colors';
                btn.innerHTML = '<i data-lucide="box" class="w-3 h-3 inline mr-1"></i> EXIT 3D';
            }

            BiosimUI.notify('3D View', 'Waddington Landscape Active  - Drag to rotate', 'inf');
        } else {
            // Switch back to 2D view
            this.canvas2d.style.display = 'block';
            this.canvas3d.style.display = 'none';

            // Update button style
            const btn = document.getElementById('3d-toggle-btn');
            if (btn) {
                btn.className = 'bg-blue-900/50 hover:bg-blue-800/80 text-[9px] text-white border border-blue-700 px-2 py-1 rounded backdrop-blur font-mono transition-colors';
                btn.innerHTML = '<i data-lucide="box" class="w-3 h-3 inline mr-1"></i> 3D LANDSCAPE';
            }
            lucide.createIcons();

            BiosimUI.notify('2D View', 'Returned to standard view', 'inf');
        }
    },

    render() {
        if (!this.active || !this.renderer) return;

        this.controls.update();
        this.renderer.render(this.scene, this.camera);
    },

    resize(width, height) {
        if (!this.camera || !this.renderer) return;

        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height);
    }
};

