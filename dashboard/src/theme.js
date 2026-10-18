// Canvas and Cesium share the same semantic colours as the interface.
const styles = getComputedStyle(document.documentElement);
export const theme = (name) => styles.getPropertyValue(`--${name}`).trim();
export const reducedMotion = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
