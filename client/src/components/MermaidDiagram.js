import React, { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';

mermaid.initialize({
  startOnLoad: true,
  theme: 'default',
  securityLevel: 'loose',
});

const MermaidDiagram = ({ chart }) => {
  const ref = useRef(null);
  const [svg, setSvg] = useState('');

  useEffect(() => {
    if (chart && ref.current) {
      const renderChart = async () => {
        try {
          const { svg } = await mermaid.render('mermaid-svg', chart);
          setSvg(svg);
        } catch (error) {
          console.error('Error rendering Mermaid diagram:', error);
          setSvg(`<pre>${chart}</pre>`);
        }
      };

      renderChart();
    }
  }, [chart]);

  return <div ref={ref} dangerouslySetInnerHTML={{ __html: svg }} />;
};

export default MermaidDiagram;