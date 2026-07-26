const THEME_INIT_CODE = `
(function() {
  try {
    var stored = localStorage.getItem('clout-theme');
    var theme = stored === 'light' || stored === 'dark'
      ? stored
      : (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    document.documentElement.setAttribute('data-theme', theme);
    document.documentElement.classList.toggle('dark', theme === 'dark');
  } catch (e) {}
})();
`;

/** Runs before paint (first thing in <body>) so the correct theme class is on
 * <html> before React hydrates — avoids a flash of the wrong theme. */
export function ThemeInitScript() {
  return <script dangerouslySetInnerHTML={{ __html: THEME_INIT_CODE }} />;
}
