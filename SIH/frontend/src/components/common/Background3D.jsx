import React, { useState, useEffect, useRef } from 'react';
import * as THREE from 'three';
import FOG from 'vanta/src/vanta.fog';

window.THREE = THREE;

export default function Background3D() {
  const [vantaEffect, setVantaEffect] = useState(null);
  const vantaRef = useRef(null);

  useEffect(() => {
    if (!vantaEffect && vantaRef.current) {
      setVantaEffect(
        FOG({
          el: vantaRef.current,
          THREE: THREE,
          mouseControls: true,
          touchControls: true,
          gyroControls: false,
          minHeight: 200.00,
          minWidth: 200.00,
          highlightColor: 0xfef3c7, // Very soft amber tint
          midtoneColor: 0xfffbeb,   // Warm cream
          lowlightColor: 0xfcd34d,  // Soft gold
          baseColor: 0xfaf9f6,      // Soft parchment base
          blurFactor: 0.8,
          speed: 0.5,
          zoom: 1.0
        })
      );
    }
    return () => {
      if (vantaEffect) vantaEffect.destroy();
    };
  }, [vantaEffect]);

  return (
    <div
      ref={vantaRef}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        zIndex: -1,
        pointerEvents: 'none' // Ensures background doesn't block clicks
      }}
    />
  );
}
