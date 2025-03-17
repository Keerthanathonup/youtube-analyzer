// static/js/network_visualization.js

// Configuration options
const config = {
    width: 800,
    height: 600,
    nodeRadius: 8,
    focusedNodeRadius: 12,
    linkDistance: 150,
    chargeStrength: -300,
    centerForce: 0.03,
    tooltipDelay: 300,
    colors: {
      // Updated colors to match red theme
      nodeDefault: "#e53e3e", // Primary red color
      nodeHighlight: "#c53030", // Darker red for highlight
      linkDefault: "#fc8181", // Lighter red for links
      linkHighlight: "#e53e3e", // Primary red for highlighted links
      textDefault: "#ffffff" // White text for better visibility
    }
  };
  
  class VideoNetworkVisualization {
    constructor(containerId, data, options = {}) {
      this.containerId = containerId;
      this.data = data;
      this.options = {...config, ...options};
      
      // Initialize variables
      this.svg = null;
      this.simulation = null;
      this.nodeElements = null;
      this.linkElements = null;
      this.textElements = null;
      this.tooltip = null;
      
      // Check if container exists
      if (!document.getElementById(this.containerId)) {
        console.error(`Container with ID '${this.containerId}' not found`);
        return;
      }
      
      // Show loading state
      this.showLoading();
      
      // Initialize the visualization
      this.initialize();
    }
    
    showLoading() {
      // Create loading element if it doesn't exist
      const container = document.getElementById(this.containerId);
      if (!container.querySelector('.network-loading')) {
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'network-loading';
        loadingDiv.innerHTML = `
          <div class="spinner"></div>
          <p>Loading network visualization...</p>
        `;
        container.appendChild(loadingDiv);
      }
    }
    
    hideLoading() {
      const loadingEl = document.getElementById(this.containerId).querySelector('.network-loading');
      if (loadingEl) {
        loadingEl.style.display = 'none';
      }
    }
    
    showError(message) {
      const container = document.getElementById(this.containerId);
      
      // Hide loading indicator
      this.hideLoading();
      
      // Create or update error element
      let errorDiv = container.querySelector('.network-error');
      if (!errorDiv) {
        errorDiv = document.createElement('div');
        errorDiv.className = 'network-error';
        errorDiv.innerHTML = `
          <p>Error loading network visualization.</p>
          <p class="error-details">${message}</p>
        `;
        container.appendChild(errorDiv);
      } else {
        errorDiv.querySelector('.error-details').textContent = message;
        errorDiv.style.display = 'block';
      }
    }
    
    initialize() {
      try {
        // Validate data
        if (!this.data || !this.data.nodes || !this.data.edges) {
          this.showError('Invalid network data structure');
          return;
        }
        
        // Create SVG container
        this.svg = d3.select(`#${this.containerId}`)
          .append("svg")
          .attr("width", this.options.width)
          .attr("height", this.options.height)
          .attr("class", "network-visualization")
          .append("g");
        
        // Add zoom behavior
        const zoom = d3.zoom()
          .scaleExtent([0.1, 3])
          .on("zoom", (event) => {
            this.svg.attr("transform", event.transform);
          });
        
        d3.select(`#${this.containerId} svg`)
          .call(zoom);
        
        // Create tooltip
        this.tooltip = d3.select(`#${this.containerId}`)
          .append("div")
          .attr("class", "network-tooltip")
          .style("opacity", 0);
        
        // Pre-process nodes to identify central node if any
        this.preprocessNodes();
        
        // Create link elements
        this.linkElements = this.svg.append("g")
          .attr("class", "links")
          .selectAll("line")
          .data(this.data.edges)
          .enter()
          .append("line")
          .attr("stroke-width", d => Math.sqrt(d.value || 1))
          .attr("stroke", this.options.colors.linkDefault);
        
        // Create node elements
        this.nodeElements = this.svg.append("g")
          .attr("class", "nodes")
          .selectAll("circle")
          .data(this.data.nodes)
          .enter()
          .append("circle")
          .attr("r", d => d.isMainNode ? this.options.focusedNodeRadius : this.options.nodeRadius)
          .attr("fill", d => this.getNodeColor(d.group))
          .call(this.setupDrag());
        
        // Add event listeners to nodes
        this.nodeElements
          .on("mouseover", (event, d) => this.handleMouseOver(event, d))
          .on("mouseout", (event, d) => this.handleMouseOut(event, d))
          .on("click", (event, d) => this.handleNodeClick(event, d));
        
        // Add text labels
        this.textElements = this.svg.append("g")
          .attr("class", "texts")
          .selectAll("text")
          .data(this.data.nodes)
          .enter()
          .append("text")
          .text(d => this.truncateText(d.title, 20))
          .attr("font-size", 12)
          .attr("dx", 15)
          .attr("dy", 4)
          .style("fill", this.options.colors.textDefault)
          .style("opacity", 0.8)
          .style("text-shadow", "0 1px 2px rgba(0,0,0,0.5)"); // Improve readability
        
        // Create force simulation
        this.simulation = d3.forceSimulation(this.data.nodes)
          .force("link", d3.forceLink(this.data.edges)
            .id(d => d.id)
            .distance(this.options.linkDistance))
          .force("charge", d3.forceManyBody().strength(this.options.chargeStrength))
          .force("center", d3.forceCenter(this.options.width / 2, this.options.height / 2))
          .force("x", d3.forceX(this.options.width / 2).strength(this.options.centerForce))
          .force("y", d3.forceY(this.options.height / 2).strength(this.options.centerForce))
          .on("tick", () => this.handleTick());
        
        // Hide loading indicator once visualization is ready
        this.hideLoading();
        
      } catch (error) {
        console.error("Error initializing network visualization:", error);
        this.showError(error.message || "Failed to initialize visualization");
      }
    }
    
    preprocessNodes() {
      // Set default positions if not provided
      this.data.nodes.forEach((node, i) => {
        // Default positioning for smoother initial layout
        if (!node.x) {
          const angle = (i / this.data.nodes.length) * 2 * Math.PI;
          const radius = Math.min(this.options.width, this.options.height) * 0.3;
          node.x = this.options.width / 2 + radius * Math.cos(angle);
          node.y = this.options.height / 2 + radius * Math.sin(angle);
        }
        
        // Ensure each node has a title
        if (!node.title) {
          node.title = `Video ${i + 1}`;
        }
      });
    }
    
    setupDrag() {
      return d3.drag()
        .on("start", (event, d) => {
          if (!event.active) this.simulation.alphaTarget(0.3).restart();
          d.fx = d.x;
          d.fy = d.y;
        })
        .on("drag", (event, d) => {
          d.fx = event.x;
          d.fy = event.y;
        })
        .on("end", (event, d) => {
          if (!event.active) this.simulation.alphaTarget(0);
          d.fx = null;
          d.fy = null;
        });
    }
    
    handleTick() {
      this.linkElements
        .attr("x1", d => d.source.x)
        .attr("y1", d => d.source.y)
        .attr("x2", d => d.target.x)
        .attr("y2", d => d.target.y);
        
      this.nodeElements
        .attr("cx", d => d.x)
        .attr("cy", d => d.y);
        
      this.textElements
        .attr("x", d => d.x)
        .attr("y", d => d.y);
    }
    
    handleMouseOver(event, d) {
      // Highlight the node
      d3.select(event.currentTarget)
        .transition()
        .duration(200)
        .attr("r", this.options.focusedNodeRadius)
        .attr("fill", this.options.colors.nodeHighlight);
      
      // Show tooltip
      this.tooltip.transition()
        .duration(200)
        .style("opacity", 0.9);
        
      this.tooltip.html(`
        <div class="tooltip-title">${d.title || "Unknown Video"}</div>
        <div class="tooltip-channel">${d.channel || ''}</div>
      `)
      .style("left", (event.pageX + 10) + "px")
      .style("top", (event.pageY - 28) + "px");
      
      // Highlight connected nodes and links
      const connectedNodeIds = this.getConnectedNodeIds(d.id);
      
      this.nodeElements.attr("opacity", node => 
        connectedNodeIds.includes(node.id) ? 1 : 0.2
      );
      
      this.linkElements
        .attr("stroke", link => 
          (link.source.id === d.id || link.target.id === d.id)
            ? this.options.colors.linkHighlight 
            : this.options.colors.linkDefault
        )
        .attr("opacity", link => 
          (link.source.id === d.id || link.target.id === d.id) ? 1 : 0.2
        )
        .attr("stroke-width", link => 
          (link.source.id === d.id || link.target.id === d.id) 
            ? Math.sqrt(link.value || 1) * 2 
            : Math.sqrt(link.value || 1)
        );
      
      this.textElements.attr("opacity", node => 
        connectedNodeIds.includes(node.id) ? 1 : 0.1
      );
    }
    
    handleMouseOut(event, d) {
      // Reset node appearance
      d3.select(event.currentTarget)
        .transition()
        .duration(200)
        .attr("r", d.isMainNode ? this.options.focusedNodeRadius : this.options.nodeRadius)
        .attr("fill", d => this.getNodeColor(d.group));
      
      // Hide tooltip
      this.tooltip.transition()
        .duration(500)
        .style("opacity", 0);
      
      // Reset all nodes and links
      this.nodeElements.attr("opacity", 1);
      this.linkElements
        .attr("stroke", this.options.colors.linkDefault)
        .attr("opacity", 1)
        .attr("stroke-width", d => Math.sqrt(d.value || 1));
      this.textElements.attr("opacity", 0.8);
    }
    
    handleNodeClick(event, d) {
      // Navigate to video details page
      window.location.href = `/video/${d.id}`;
    }
    
    getConnectedNodeIds(nodeId) {
      const connectedNodeIds = [nodeId]; // Include the node itself
      
      this.data.edges.forEach(link => {
        const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
        const targetId = typeof link.target === 'object' ? link.target.id : link.target;
        
        if (sourceId === nodeId && !connectedNodeIds.includes(targetId)) {
          connectedNodeIds.push(targetId);
        } else if (targetId === nodeId && !connectedNodeIds.includes(sourceId)) {
          connectedNodeIds.push(sourceId);
        }
      });
      
      return connectedNodeIds;
    }
    
    getNodeColor(group) {
      // Generate colors based on group value for different node types
      const colors = [
        "#e53e3e", // Group 1 - Primary red
        "#dd6b20", // Group 2 - Orange
        "#d69e2e", // Group 3 - Yellow
        "#38a169", // Group 4 - Green
        "#3182ce", // Group 5 - Blue
        "#805ad5", // Group 6 - Purple
        "#d53f8c", // Group 7 - Pink
        "#b83280", // Group 8 - Darker pink
        "#6b46c1"  // Group 9 - Indigo
      ];
      
      // Ensure we have a valid group number
      const groupIndex = typeof group === 'number' && group > 0 
        ? Math.min(group, colors.length) - 1 
        : 0;
        
      return colors[groupIndex];
    }
    
    truncateText(text, maxLength) {
      if (!text) return "";
      return text.length > maxLength ? text.substring(0, maxLength) + "..." : text;
    }
    
    // Public methods
    updateData(newData) {
      if (!newData || !newData.nodes || !newData.edges) {
        console.error("Invalid data format for updateData");
        return;
      }
      
      this.data = newData;
      
      // Preprocess nodes
      this.preprocessNodes();
      
      // Update link data
      this.linkElements = this.linkElements.data(this.data.edges, d => `${d.source}-${d.target}`);
      this.linkElements.exit().remove();
      
      const newLinks = this.linkElements.enter()
        .append("line")
        .attr("stroke-width", d => Math.sqrt(d.value || 1))
        .attr("stroke", this.options.colors.linkDefault);
        
      this.linkElements = newLinks.merge(this.linkElements);
      
      // Update node data
      this.nodeElements = this.nodeElements.data(this.data.nodes, d => d.id);
      this.nodeElements.exit().remove();
      
      const newNodes = this.nodeElements.enter()
        .append("circle")
        .attr("r", d => d.isMainNode ? this.options.focusedNodeRadius : this.options.nodeRadius)
        .attr("fill", d => this.getNodeColor(d.group))
        .call(this.setupDrag())
        .on("mouseover", (event, d) => this.handleMouseOver(event, d))
        .on("mouseout", (event, d) => this.handleMouseOut(event, d))
        .on("click", (event, d) => this.handleNodeClick(event, d));
        
      this.nodeElements = newNodes.merge(this.nodeElements);
      
      // Update text labels
      this.textElements = this.textElements.data(this.data.nodes, d => d.id);
      this.textElements.exit().remove();
      
      const newTexts = this.textElements.enter()
        .append("text")
        .text(d => this.truncateText(d.title, 20))
        .attr("font-size", 12)
        .attr("dx", 15)
        .attr("dy", 4)
        .style("fill", this.options.colors.textDefault)
        .style("opacity", 0.8)
        .style("text-shadow", "0 1px 2px rgba(0,0,0,0.5)");
        
      this.textElements = newTexts.merge(this.textElements);
      
      // Update simulation
      this.simulation.nodes(this.data.nodes);
      this.simulation.force("link").links(this.data.edges);
      this.simulation.alpha(1).restart();
    }
    
    focusNode(nodeId) {
      const node = this.data.nodes.find(n => n.id === nodeId);
      if (node) {
        // Mark as main node
        node.isMainNode = true;
        
        // Center the view on the node
        const containerElement = document.getElementById(this.containerId);
        if (!containerElement) return;
        
        const svgElement = containerElement.querySelector("svg");
        if (!svgElement) return;
        
        const transform = d3.zoomTransform(svgElement);
        
        const scale = 1.2;
        const x = this.options.width / 2 - node.x * scale;
        const y = this.options.height / 2 - node.y * scale;
        
        d3.select(svgElement)
          .transition()
          .duration(750)
          .call(
            d3.zoom().transform,
            d3.zoomIdentity.translate(x, y).scale(scale)
          );
          
        // Highlight the node
        this.nodeElements
          .filter(d => d.id === nodeId)
          .transition()
          .duration(500)
          .attr("r", this.options.focusedNodeRadius * 1.2)
          .attr("fill", this.options.colors.nodeHighlight)
          .attr("stroke", "#fff")
          .attr("stroke-width", 2);
        
        // Highlight the text
        this.textElements
          .filter(d => d.id === nodeId)
          .transition()
          .duration(500)
          .attr("font-weight", "bold")
          .style("opacity", 1);
      }
    }
    
    resize() {
      // Get new container dimensions
      const containerElement = document.getElementById(this.containerId);
      if (!containerElement) return;
      
      const width = containerElement.clientWidth;
      const height = containerElement.clientHeight || 500; // Default height if not specified
      
      // Update configuration
      this.options.width = width;
      this.options.height = height;
      
      // Update SVG dimensions
      d3.select(`#${this.containerId} svg`)
        .attr("width", width)
        .attr("height", height);
      
      // Update forces
      this.simulation
        .force("center", d3.forceCenter(width / 2, height / 2))
        .force("x", d3.forceX(width / 2).strength(this.options.centerForce))
        .force("y", d3.forceY(height / 2).strength(this.options.centerForce));
      
      // Restart simulation
      this.simulation.alpha(0.3).restart();
    }
  }
  
  // Initialize network visualization with API data
  function initNetworkVisualization(containerId, apiEndpoint, centralVideoId = null) {
    const container = document.getElementById(containerId);
    if (!container) {
      console.error(`Container with ID '${containerId}' not found`);
      return;
    }
    
    // Show loading indicator
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'network-loading';
    loadingDiv.innerHTML = `
      <div class="spinner"></div>
      <p>Loading network data...</p>
    `;
    container.appendChild(loadingDiv);
    
    // Fetch network data from API
    fetch(apiEndpoint)
      .then(response => {
        if (!response.ok) {
          throw new Error(`HTTP error ${response.status}`);
        }
        return response.json();
      })
      .then(data => {
        // Make sure we have valid data
        if (!data || !data.nodes || !data.edges) {
          throw new Error('Invalid data format received from API');
        }
        
        // Mark central node if specified
        if (centralVideoId && data.nodes) {
          data.nodes.forEach(node => {
            if (node.id === centralVideoId) {
              node.isMainNode = true;
            }
          });
        }
        
        // Create visualization
        const networkViz = new VideoNetworkVisualization(containerId, data, {
          width: container.clientWidth,
          height: 600
        });
        
        // Focus on central node if provided
        if (centralVideoId) {
          setTimeout(() => networkViz.focusNode(centralVideoId), 1000);
        }
        
        // Add window resize handler
        window.addEventListener('resize', () => networkViz.resize());
        
        // Save reference to visualization instance
        window.networkViz = networkViz;
      })
      .catch(error => {
        console.error("Error loading network data:", error);
        // Remove loading indicator
        const loadingEl = container.querySelector('.network-loading');
        if (loadingEl) {
          loadingEl.style.display = 'none';
        }
        
        // Show error message
        container.innerHTML = `
          <div class="network-error">
            <p>Error loading network visualization.</p>
            <p class="error-details">${error.message || 'Network request failed'}</p>
          </div>
        `;
      });
  }