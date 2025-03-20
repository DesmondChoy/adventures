
import React, { useEffect, useState } from 'react';

const colors = [
  'bg-odyssey-blue',
  'bg-odyssey-teal',
  'bg-odyssey-purple',
  'bg-odyssey-lavender',
  'bg-odyssey-pink',
  'bg-odyssey-coral',
  'bg-odyssey-yellow',
  'bg-odyssey-green'
];

interface ConfettiProps {
  count?: number;
  duration?: number;
}

const Confetti: React.FC<ConfettiProps> = ({ count = 50, duration = 2000 }) => {
  const [confettiElements, setConfettiElements] = useState<React.ReactNode[]>([]);

  useEffect(() => {
    const elements = [];
    
    for (let i = 0; i < count; i++) {
      const color = colors[Math.floor(Math.random() * colors.length)];
      const left = `${Math.random() * 100}%`;
      const size = `${Math.random() * 0.5 + 0.5}rem`;
      const delay = `${Math.random() * 0.5}s`;
      const initialRotation = Math.floor(Math.random() * 360);
      
      elements.push(
        <div 
          key={i}
          className={`confetti-item ${color} animate-confetti`}
          style={{
            left,
            width: size,
            height: size,
            top: '-20px',
            animationDelay: delay,
            transform: `rotate(${initialRotation}deg)`,
            animationDuration: `${duration / 1000 + Math.random()}s`
          }}
        />
      );
    }
    
    setConfettiElements(elements);
    
    const timer = setTimeout(() => {
      setConfettiElements([]);
    }, duration + 1000);
    
    return () => clearTimeout(timer);
  }, [count, duration]);

  return <div className="fixed top-0 left-0 w-full h-full pointer-events-none overflow-hidden z-50">{confettiElements}</div>;
};

export default Confetti;
