document.addEventListener('DOMContentLoaded', function() {
    // Tab switching
    document.querySelectorAll('.tab-btn').forEach(button => {
        button.addEventListener('click', function() {
            // Hide all panels
            document.querySelectorAll('.tab-panel').forEach(panel => {
                panel.classList.remove('active');
            });
            
            // Show selected panel
            document.getElementById(this.getAttribute('data-tab')).classList.add('active');
            
            // Update button states
            document.querySelectorAll('.tab-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            this.classList.add('active');
        });
    });
    
    // Summary type switching
    document.querySelectorAll('.summary-btn').forEach(button => {
        button.addEventListener('click', function() {
            // Hide all content
            document.querySelectorAll('.summary-content').forEach(content => {
                content.classList.remove('active');
            });
            
            // Show selected content
            document.getElementById(this.getAttribute('data-summary') + '-summary').classList.add('active');
            
            // Update button states
            document.querySelectorAll('.summary-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            this.classList.add('active');
        });
    });
});