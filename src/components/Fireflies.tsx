'use client';

import { useEffect, useRef } from 'react';
import * as THREE from 'three';

interface Fly {
  pos: THREE.Vector3;
  vel: THREE.Vector3;
  phase: number;
  twinkleSpeed: number;
  brightness: number;
}

function randomIn(x: number, y: number, z: number) {
  return new THREE.Vector3(
    (Math.random() * 2 - 1) * x,
    (Math.random() * 2 - 1) * y,
    (Math.random() * 2 - 1) * z
  );
}

export default function Fireflies() {
  const containerRef = useRef<HTMLDivElement>(null);
  const frameRef = useRef<number>(0);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(
      45,
      container.clientWidth / container.clientHeight,
      0.1,
      100
    );
    camera.position.z = 22;

    const renderer = new THREE.WebGLRenderer({ antialias: false, alpha: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.25));
    renderer.domElement.style.width = '100%';
    renderer.domElement.style.height = '100%';
    renderer.domElement.style.display = 'block';
    container.appendChild(renderer.domElement);

    // Soft radial sprite so points read as glows, not squares.
    const spriteSize = 64;
    const spriteCanvas = document.createElement('canvas');
    spriteCanvas.width = spriteCanvas.height = spriteSize;
    const ctx = spriteCanvas.getContext('2d')!;
    const grad = ctx.createRadialGradient(
      spriteSize / 2, spriteSize / 2, 0,
      spriteSize / 2, spriteSize / 2, spriteSize / 2
    );
    grad.addColorStop(0, 'rgba(255,224,150,0.85)');
    grad.addColorStop(0.3, 'rgba(251,191,36,0.42)');
    grad.addColorStop(1, 'rgba(251,191,36,0)');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, spriteSize, spriteSize);
    const texture = new THREE.CanvasTexture(spriteCanvas);

    const bounds = { x: 11.5, y: 8.5, z: 5 };
    const groups = [
      { count: 18, size: 1.0, zDepth: 3, brightness: 1.0 },
      { count: 55, size: 0.42, zDepth: 8, brightness: 0.55 },
    ];

    const systems: { points: THREE.Points; geo: THREE.BufferGeometry; flies: Fly[] }[] = [];

    for (const group of groups) {
      const positions = new Float32Array(group.count * 3);
      const colors = new Float32Array(group.count * 3);
      const flies: Fly[] = [];
      for (let i = 0; i < group.count; i++) {
        const pos = randomIn(bounds.x, bounds.y, group.zDepth);
        const fly: Fly = {
          pos,
          vel: new THREE.Vector3(),
          phase: Math.random() * Math.PI * 2,
          twinkleSpeed: 0.6 + Math.random() * 1.6,
          brightness: group.brightness * (0.6 + Math.random() * 0.4),
        };
        flies.push(fly);
        positions.set([pos.x, pos.y, pos.z], i * 3);
      }
      const geo = new THREE.BufferGeometry();
      geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
      geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));
      const mat = new THREE.PointsMaterial({
        size: group.size,
        map: texture,
        vertexColors: true,
        transparent: true,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      });
      const points = new THREE.Points(geo, mat);
      scene.add(points);
      systems.push({ points, geo, flies });
    }

    let time = 0;
    function animate() {
      frameRef.current = requestAnimationFrame(animate);
      time += 0.016;

      for (const { geo, flies } of systems) {
        const arr = geo.attributes.position.array as Float32Array;
        const col = geo.attributes.color!.array as Float32Array;
        for (let i = 0; i < flies.length; i++) {
          const fly = flies[i];
          // Gentle wander
          fly.vel.x += Math.sin(time * 0.9 + fly.phase) * 0.0016;
          fly.vel.y += Math.cos(time * 0.7 + fly.phase * 1.7) * 0.0016;
          fly.vel.z += Math.sin(time * 0.5 + i) * 0.0006;
          // Occasional dart, the way a real fly breaks off
          if (Math.random() < 0.0022) {
            const target = randomIn(bounds.x, bounds.y, 4);
            fly.vel.subVectors(target, fly.pos).multiplyScalar(0.06);
          }
          fly.vel.multiplyScalar(0.965);
          fly.pos.add(fly.vel);
          // Soft bounds: steer back toward the field rather than bounce
          if (Math.abs(fly.pos.x) > bounds.x) fly.vel.x -= Math.sign(fly.pos.x) * 0.01;
          if (Math.abs(fly.pos.y) > bounds.y) fly.vel.y -= Math.sign(fly.pos.y) * 0.01;
          if (Math.abs(fly.pos.z) > bounds.z) fly.vel.z -= Math.sign(fly.pos.z) * 0.01;
          arr.set([fly.pos.x, fly.pos.y, fly.pos.z], i * 3);
          // Twinkle: mostly on, slow pulse
          const pulse = 0.45 + 0.55 * Math.pow(0.5 + 0.5 * Math.sin(time * fly.twinkleSpeed + fly.phase), 2);
          const b = fly.brightness * pulse;
          col.set([b, b * 0.75, b * 0.3], i * 3);
        }
        geo.attributes.position.needsUpdate = true;
        geo.attributes.color!.needsUpdate = true;
      }

      renderer.render(scene, camera);
    }
    animate();

    function onResize() {
      if (!container) return;
      camera.aspect = container.clientWidth / container.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(container.clientWidth, container.clientHeight);
    }
    window.addEventListener('resize', onResize);

    return () => {
      window.removeEventListener('resize', onResize);
      cancelAnimationFrame(frameRef.current);
      for (const { points, geo } of systems) {
        scene.remove(points);
        geo.dispose();
        (points.material as THREE.Material).dispose();
      }
      texture.dispose();
      renderer.dispose();
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
    };
  }, []);

  return (
    <div
      ref={containerRef}
      className="w-full h-[340px] md:h-[480px]"
      style={{ pointerEvents: 'none' }}
      aria-hidden="true"
    />
  );
}
