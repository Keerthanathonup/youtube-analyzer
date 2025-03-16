import os
import shutil

# Ensure static directory exists
os.makedirs("static/css", exist_ok=True)

# Create the CSS file directly
css_content = """
/* Basic styling for YouTube Analyzer */
body {
    font-family: Arial, sans-serif;
    line-height: 1.6;
    margin: 0;
    padding: 20px;
    max-width: 1200px;
    margin: 0 auto;
}

header {
    margin-bottom: 20px;
}

h1, h2, h3 {
    color: #333;
}

.video-container {
    margin-bottom: 30px;
}

.video-details {
    display: flex;
    margin-bottom: 20px;
}

.video-thumbnail {
    margin-right: 20px;
    max-width: 320px;
}

.video-info {
    flex: 1;
}

.analysis-section {
    margin-top: 30px;
    padding: 20px;
    background-color: #f9f9f9;
    border-radius: 5px;
}

.key-points {
    list-style-type: none;
    padding-left: 0;
}

.key-points li {
    margin-bottom: 10px;
    padding-left: 20px;
    position: relative;
}

.key-points li:before {
    content: "•";
    position: absolute;
    left: 0;
    color: #0066cc;
}

.search-form {
    margin-bottom: 20px;
}

.search-form input[type="text"] {
    padding: 8px;
    width: 300px;
}

.search-form button {
    padding: 8px 16px;
    background-color: #0066cc;
    color: white;
    border: none;
    cursor: pointer;
}

.video-list {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 20px;
}

.video-card {
    border: 1px solid #ddd;
    border-radius: 5px;
    padding: 15px;
    transition: transform 0.2s;
}

.video-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 5px 15px rgba(0,0,0,0.1);
}

.video-card img {
    width: 100%;
    height: auto;
}

a {
    color: #0066cc;
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
}
"""

# Write the CSS file
with open("static/css/styles.css", "w") as f:
    f.write(css_content)

# Check HTML templates and update if needed
template_dir = "templates"
for root, _, files in os.walk(template_dir):
    for file in files:
        if file.endswith(".html"):
            file_path = os.path.join(root, file)
            with open(file_path, "r") as f:
                content = f.read()
            
            # Make sure CSS is referenced correctly
            if "<head>" in content and '/static/css/styles.css' not in content:
                content = content.replace("<head>", 
                                         '<head>\n    <link rel="stylesheet" href="/static/css/styles.css">')
                with open(file_path, "w") as f:
                    f.write(content)
                print(f"Updated CSS reference in {file_path}")

print("Static files setup complete!")