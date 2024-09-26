import React, { useEffect, useRef } from 'react';
import mermaid from 'mermaid';

const MermaidDiagram = ({ chart }) => {
  const ref = useRef(null);

  useEffect(() => {
    mermaid.initialize({
      startOnLoad: true,
      theme: 'default',
      securityLevel: 'loose',
    });

    const renderChart = async () => {
      if (ref.current) {
        try {
          // Ensure the chart starts with a valid diagram type
          const modifiedChart = chart.trim().startsWith('graph') ? chart : `graph LR\n${chart}`;
          const { svg } = await mermaid.render('mermaid-diagram', modifiedChart);
          ref.current.innerHTML = svg;
        } catch (error) {
          console.error('Mermaid rendering error:', error);
          ref.current.innerHTML = `
            <div style="color: red; border: 1px solid red; padding: 10px;">
              <p>Error rendering diagram: ${error.message}</p>
              <pre>${chart}</pre>
            </div>
          `;
        }
      }
    };

    renderChart();
  }, [chart]);

  return <div ref={ref} />;
};

export default MermaidDiagram;