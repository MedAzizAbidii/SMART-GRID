import { useRef } from "react";

/** Accumulates real polled values into a rolling client-side history so
 * sparklines/charts show genuine session data instead of fabricated series.
 * Call on every render with the latest value; returns the array so far. */
export function useHistorySeries(value, maxLen = 30) {
  const ref = useRef([]);
  if (value !== undefined && value !== null && !Number.isNaN(value)) {
    const arr = ref.current;
    if (arr.length === 0 || arr[arr.length - 1] !== value) {
      arr.push(value);
      if (arr.length > maxLen) arr.shift();
    }
  }
  return ref.current;
}
