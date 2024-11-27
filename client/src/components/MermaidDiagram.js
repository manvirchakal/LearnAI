import React, { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';

const MermaidDiagram = ({ chart, index }) => {
  const ref = useRef(null);
  const [retryCount, setRetryCount] = useState(0);
  const maxRetries = 3;

  useEffect(() => {
    mermaid.initialize({
      startOnLoad: true,
      theme: 'default',
      securityLevel: 'loose',
      htmlLabels: true,
      fontSize: 16,
      flowchart: {
        useMaxWidth: false,
        htmlLabels: true,
        curve: 'basis',
        rankSpacing: 50,
        nodeSpacing: 50,
      }
    });

    const renderChart = async () => {
      if (!ref.current) return;

      try {
        const id = `mermaid-diagram-${index}`;
        ref.current.innerHTML = '';
        const newDiv = document.createElement('div');
        newDiv.id = id;
        newDiv.textContent = chart;
        ref.current.appendChild(newDiv);

        await new Promise(resolve => setTimeout(resolve, 100));
        
        if (document.getElementById(id)) {
          await mermaid.run({ nodes: [newDiv] });
          const svg = ref.current.querySelector('svg');
          if (svg) {
            svg.style.width = 'auto';
            svg.style.height = 'auto';
            svg.style.maxWidth = '90%';
            svg.style.maxHeight = '90%';
            svg.style.margin = 'auto';
          }
        } else if (retryCount < maxRetries) {
          setRetryCount(prev => prev + 1);
        }
      } catch (error) {
        console.error('Mermaid rendering error:', error);
        if (retryCount < maxRetries) {
          setRetryCount(prev => prev + 1);
        } else {
          ref.current.innerHTML = `
            <div style="color: red; border: 1px solid red; padding: 10px;">
              <p>Error rendering diagram. Please check the diagram syntax.</p>
              <pre>${chart}</pre>
            </div>
          `;
        }
      }
    };

    const timer = setTimeout(() => {
      renderChart();
    }, 200);

    return () => clearTimeout(timer);
  }, [chart, index, retryCount]);

  return (
    <div 
      ref={ref} 
      style={{ 
        width: '100%',
        height: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        overflow: 'hidden'
      }} 
    />
  );
};

export default MermaidDiagram;