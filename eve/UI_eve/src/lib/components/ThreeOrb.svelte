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
    const targetColor = new THREE.Color();
    const currentColor = new THREE.Color();
    let targetSpeed = 0.001;
    let currentSpeed = 0.001;
    let targetScale = 1.0;
    let currentScale = 1.0;
    const stateConfigs = {
        Idle: { color: 0x4ae5ff, speed: 0.001, scale: 1.0 },
        Listening: { color: 0x00ffff, speed: 0.004, scale: 1.05 },
        Thinking: { color: 0xb34aff, speed: 0.005, scale: 1.0 },
        Speaking: { color: 0xffffff, speed: 0.002, scale: 1.1 },
        Searching: { color: 0x00ff88, speed: 0.006, scale: 1.0 },
        ExecutingTool: { color: 0xffaa00, speed: 0.004, scale: 1.0 },
        Error: { color: 0xff3333, speed: 0.01, scale: 0.95 },
    };
    $: {
        const config =
            stateConfigs[$currentState as keyof typeof stateConfigs] ||
            stateConfigs["Idle"];
        targetColor.setHex(config.color);
        targetSpeed = config.speed;
        targetScale = config.scale;
    }

    onMount(() => {
        initScene();
        animate();

        window.addEventListener("resize", onWindowResize);
    });

    onDestroy(() => {
        if (typeof window !== "undefined") {
            window.removeEventListener("resize", onWindowResize);
        }
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
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        container.appendChild(renderer.domElement);

        const particleCount = 8000;
        const geometry = new THREE.BufferGeometry();
        const positions = new Float32Array(particleCount * 3);
        const radius = 60;

        for (let i = 0; i < particleCount; i++) {
            // Math for uniform point distribution on a sphere surface (with slight volume)
            const theta = Math.random() * Math.PI * 2;
            const phi = Math.acos(Math.random() * 2 - 1);

            // Add some depth variance (shell thickness)
            const r = radius - Math.random() * 15;

            positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
            positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
            positions[i * 3 + 2] = r * Math.cos(phi);
        }

        geometry.setAttribute(
            "position",
            new THREE.BufferAttribute(positions, 3),
        );

        const material = new THREE.PointsMaterial({
            color: 0x4ae5ff,
            size: 1.2,
            transparent: true,
            opacity: 0.8,
            blending: THREE.AdditiveBlending,
            depthWrite: false,
        });

        particleSystem = new THREE.Points(geometry, material);
        scene.add(particleSystem);
        currentColor.setHex(stateConfigs["Idle"].color);
    }

    function animate() {
        animationId = requestAnimationFrame(animate);
        currentColor.lerp(targetColor, 0.05);
        currentSpeed += (targetSpeed - currentSpeed) * 0.05;
        currentScale += (targetScale - currentScale) * 0.1;
        let scaleMod = currentScale;
        if ($currentState === "Speaking") {
            scaleMod += Math.sin(Date.now() * 0.01) * 0.03;
        }

        particleSystem.scale.set(scaleMod, scaleMod, scaleMod);

        (particleSystem.material as THREE.PointsMaterial).color.copy(
            currentColor,
        );

        particleSystem.rotation.y += currentSpeed;
        particleSystem.rotation.x += currentSpeed * 0.5;

        renderer.render(scene, camera);
    }

    function onWindowResize() {
        if (!camera || !renderer) return;
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
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
