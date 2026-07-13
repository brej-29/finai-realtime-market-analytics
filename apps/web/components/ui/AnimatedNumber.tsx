"use client";

import { useEffect, useRef } from "react";

import { animate, useMotionValue, useMotionValueEvent } from "motion/react";

interface Props {
  value: number;
  formatter?: (value: number) => string;
  className?: string;
}

/** Spring-animated number that counts toward `value` whenever it changes. */
export function AnimatedNumber({ value, formatter, className }: Props) {
  const spanRef = useRef<HTMLSpanElement | null>(null);
  const motionValue = useMotionValue(value);
  const hasMounted = useRef(false);

  useMotionValueEvent(motionValue, "change", (latest) => {
    if (spanRef.current) {
      spanRef.current.textContent = formatter ? formatter(latest) : latest.toFixed(2);
    }
  });

  useEffect(() => {
    if (!hasMounted.current) {
      hasMounted.current = true;
      motionValue.set(value);
      if (spanRef.current) {
        spanRef.current.textContent = formatter ? formatter(value) : value.toFixed(2);
      }
      return;
    }
    const controls = animate(motionValue, value, {
      type: "spring",
      stiffness: 120,
      damping: 20
    });
    return () => controls.stop();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  return (
    <span ref={spanRef} className={className}>
      {formatter ? formatter(value) : value.toFixed(2)}
    </span>
  );
}
