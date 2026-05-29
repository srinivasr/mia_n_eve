<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import * as THREE from "three";
    import { currentState } from "../stores/eveState";

    let container: HTMLDivElement;
    let animationId: number;
    let renderer: THREE.WebGLRenderer;
    let scene: THREE.Scene;
    let camera: THREE.PerspectiveCamera;
    let particleSystem: THREE.Points;
    let shaderMaterial: THREE.ShaderMaterial;

    const targetColor = new THREE.Color();
    const currentColor = new THREE.Color();
    let targetSpeed = 0.001;
    let currentSpeed = 0.001;
    let targetScale = 1.0;
    let currentScale = 1.0;
    let targetBreathIntensity = 0.3;
    let currentBreathIntensity = 0.3;

    const stateConfigs: Record<
        string,
        { color: number; speed: number; scale: number; breathIntensity: number }
    > = {
        Idle: {
            color: 0x4ae5ff,
            speed: 0.003,
            scale: 1.0,
            breathIntensity: 0.3,
        },
        Listening: {
            color: 0x00ffff,
            speed: 0.012,
            scale: 1.05,
            breathIntensity: 0.5,
        },
        Thinking: {
            color: 0xb34aff,
            speed: 0.015,
            scale: 1.0,
            breathIntensity: 0.6,
        },
        Speaking: {
            color: 0xffffff,
            speed: 0.006,
            scale: 1.1,
            breathIntensity: 0.8,
        },
        Searching: {
            color: 0x00ff88,
            speed: 0.018,
            scale: 1.0,
            breathIntensity: 0.5,
        },
        ExecutingTool: {
            color: 0xffaa00,
            speed: 0.012,
            scale: 1.0,
            breathIntensity: 0.4,
        },
        Error: {
            color: 0xff3333,
            speed: 0.03,
            scale: 0.95,
            breathIntensity: 1.0,
        },
    };

    $: {
        const config =
            stateConfigs[$currentState as keyof typeof stateConfigs] ||
            stateConfigs["Idle"];
        targetColor.setHex(config.color);
        targetSpeed = config.speed;
        targetScale = config.scale;
        targetBreathIntensity = config.breathIntensity;
    }

    // ── GLSL Shaders ──────────────────────────────────────────────────
    const vertexShader = /* glsl */ `
        attribute float aSize;
        attribute float aPhase;
        attribute float aOpacity;

        uniform float uTime;
        uniform float uBreathIntensity;
        uniform float uPixelRatio;

        varying float vOpacity;
        varying float vDistFromCenter;

        void main() {
            float dist = length(position);
            vDistFromCenter = clamp(dist / 30.0, 0.0, 1.0);

            // Each particle breathes at its own rhythm
            float breath = sin(uTime * 2.0 + aPhase) * 0.5 + 0.5;
            float sizeMod = 1.0 + breath * uBreathIntensity;

            // Particles closer to center render larger
            float centerBoost = 1.0 + (1.0 - vDistFromCenter) * 0.5;

            // Opacity pulses with the breath
            vOpacity = aOpacity * (0.6 + breath * 0.4);

            vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
            gl_PointSize = aSize * sizeMod * centerBoost * uPixelRatio * (200.0 / -mvPosition.z);
            gl_Position = projectionMatrix * mvPosition;
        }
    `;

    const fragmentShader = /* glsl */ `
        uniform vec3 uColor;

        varying float vOpacity;
        varying float vDistFromCenter;

        void main() {
            // Soft circular glow instead of a hard square
            float d = length(gl_PointCoord - vec2(0.5));
            if (d > 0.5) discard;

            float alpha = 1.0 - smoothstep(0.0, 0.5, d);
            alpha *= alpha;  // quadratic falloff for softer edges

            // Core particles glow brighter
            float coreBrightness = 1.0 + (1.0 - vDistFromCenter) * 0.3;
            vec3 finalColor = uColor * coreBrightness;

            gl_FragColor = vec4(finalColor, alpha * vOpacity);
        }
    `;

    let resizeObserver: ResizeObserver;

    onMount(() => {
        initScene();
        animate();

        resizeObserver = new ResizeObserver((entries) => {
            for (let entry of entries) {
                const { width, height } = entry.contentRect;
                if (width && height) {
                    onWindowResize(width, height);
                }
            }
        });
        resizeObserver.observe(container);
    });

    onDestroy(() => {
        if (resizeObserver && container) resizeObserver.unobserve(container);
        if (animationId) cancelAnimationFrame(animationId);
        if (renderer) renderer.dispose();
    });

    function initScene() {
        scene = new THREE.Scene();

        camera = new THREE.PerspectiveCamera(
            45,
            window.innerWidth / window.innerHeight,
            1,
            1000,
        );
        camera.position.z = 250;
        renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });

        container.appendChild(renderer.domElement);

        // ── Particle geometry ─────────────────────────────────────────
        const particleCount = 25000;
        const geometry = new THREE.BufferGeometry();
        const positions = new Float32Array(particleCount * 3);
        const sizes = new Float32Array(particleCount);
        const phases = new Float32Array(particleCount);
        const opacities = new Float32Array(particleCount);
        const radius = 35;

        for (let i = 0; i < particleCount; i++) {
            const theta = Math.random() * Math.PI * 2;
            const phi = Math.acos(Math.random() * 2 - 1);
            const r = radius - Math.random() * 15;

            positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
            positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
            positions[i * 3 + 2] = r * Math.cos(phi);

            // Per-particle variation
            sizes[i] = 0.5 + Math.random() * 2.5; // 0.5 – 3.0
            phases[i] = Math.random() * Math.PI * 2; // desync breathing
            opacities[i] = 0.4 + Math.random() * 0.6; // 0.4 – 1.0
        }

        geometry.setAttribute(
            "position",
            new THREE.BufferAttribute(positions, 3),
        );
        geometry.setAttribute("aSize", new THREE.BufferAttribute(sizes, 1));
        geometry.setAttribute("aPhase", new THREE.BufferAttribute(phases, 1));
        geometry.setAttribute(
            "aOpacity",
            new THREE.BufferAttribute(opacities, 1),
        );

        // ── Custom shader material ────────────────────────────────────
        shaderMaterial = new THREE.ShaderMaterial({
            vertexShader,
            fragmentShader,
            uniforms: {
                uTime: { value: 0.0 },
                uColor: { value: new THREE.Color(0x4ae5ff) },
                uBreathIntensity: { value: 0.3 },
                uPixelRatio: { value: Math.min(window.devicePixelRatio, 2) },
            },
            transparent: true,
            blending: THREE.AdditiveBlending,
            depthWrite: false,
        });

        particleSystem = new THREE.Points(geometry, shaderMaterial);
        particleSystem.position.y = 20;
        scene.add(particleSystem);
        currentColor.setHex(stateConfigs["Idle"].color);
    }

    let lastTime = performance.now();

    function animate() {
        animationId = requestAnimationFrame(animate);

        const currentTime = performance.now();
        // Normalize delta time to 60fps (~16.66ms per frame)
        // This ensures the orb rotates at the exact same speed even if the framerate lags
        const dt = (currentTime - lastTime) / 16.666;
        lastTime = currentTime;

        // Smooth lerped transitions (also scaled by dt for smooth state changes)
        currentColor.lerp(targetColor, 0.15 * dt);
        currentSpeed += (targetSpeed - currentSpeed) * 0.15 * dt;
        currentScale += (targetScale - currentScale) * 0.2 * dt;
        currentBreathIntensity +=
            (targetBreathIntensity - currentBreathIntensity) * 0.1 * dt;

        let scaleMod = currentScale;
        if ($currentState === "Speaking") {
            scaleMod += Math.sin(Date.now() * 0.01) * 0.03;
        }

        particleSystem.scale.set(scaleMod, scaleMod, scaleMod);

        // Drive the shader
        shaderMaterial.uniforms.uTime.value = Date.now() * 0.001;
        shaderMaterial.uniforms.uColor.value.copy(currentColor);
        shaderMaterial.uniforms.uBreathIntensity.value = currentBreathIntensity;

        // Apply frame-rate independent rotation
        particleSystem.rotation.y += currentSpeed * dt;
        particleSystem.rotation.x += currentSpeed * 0.5 * dt;

        renderer.render(scene, camera);
    }

    function onWindowResize(w: number, h: number) {
        if (!camera || !renderer) return;
        if (h === 0) h = 1;
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
        renderer.setSize(w, h);
    }
</script>

<div bind:this={container} class="canvas-container"></div>

<style>
    .canvas-container {
        position: absolute;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        overflow: hidden;
        pointer-events: none;
        z-index: 10;
    }
</style>
