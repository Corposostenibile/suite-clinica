document$.subscribe(function() {
  mermaid.initialize({
    startOnLoad: false,
    theme: 'base',
    themeVariables: {
      primaryColor: '#d1fae5',
      primaryTextColor: '#065f46',
      primaryBorderColor: '#10b981',
      lineColor: '#6b7280',
    },
    securityLevel: 'loose',
  });
  mermaid.run({
    querySelector: '.mermaid',
  });
});
