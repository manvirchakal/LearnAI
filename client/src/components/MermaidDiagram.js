import React, { useEffect, useRef } from 'react';
import mermaid from 'mermaid';

const MermaidDiagram = ({ chart, index }) => {
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
          const id = `mermaid-diagram-${index}`;
          ref.current.innerHTML = ''; // Clear previous content
          const newDiv = document.createElement('div');
          newDiv.id = id;
          newDiv.textContent = chart;
          ref.current.appendChild(newDiv);
          await mermaid.run({ nodes: [newDiv] });
        } catch (error) {
          console.error('Mermaid rendering error:', error);
          ref.current.innerHTML = `
            <div style="color: red; border: 1px solid red; padding: 10px;">
              <p>Error rendering diagram. Please check the diagram syntax.</p>
              <pre>${chart}</pre>
            </div>
          `;
        }
      }
    };

    renderChart();
  }, [chart, index]);

  return <div ref={ref} style={{ marginBottom: '20px' }} />;
};

export default MermaidDiagram;