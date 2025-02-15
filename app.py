from flask import Flask, request, send_file, render_template_string
from PIL import Image, ImageEnhance
from pathlib import Path
import yaml
from resizeimage import resizeimage
import logging
from rembg import remove
import io
import zipfile
from datetime import datetime
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('image_processor.log'),
        logging.StreamHandler()
    ]
)

class ProductImageProcessor:
    def __init__(self, config_path=None):
        self.config = self._load_config(config_path)
        
    def _load_config(self, config_path):
        default_config = {
            'dimensions': {'width': 1200, 'height': 1200},
            'output_format': 'JPEG',
            'quality': 95,
            'operations': {
                'resize': True,
                'remove_background': False,
                'enhance': True,
                'watermark': False
            },
            'backgrounds': {
                'default_color': "#FFFFFF",
                'gradient': False
            }
        }
        
        if config_path and Path(config_path).exists():
            with open(config_path, 'r') as f:
                return {**default_config, **yaml.safe_load(f)}
        return default_config

    def process_image(self, image):
        """Process a single image according to configuration settings."""
        try:
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Resize if configured
            if self.config['operations']['resize']:
                image = resizeimage.resize_contain(
                    image,
                    [self.config['dimensions']['width'], 
                     self.config['dimensions']['height']]
                )
            
            # Remove background if configured
            if self.config['operations']['remove_background']:
                # Remove background
                image = remove(image)
                # After background removal, we need to handle transparency
                if image.mode == 'RGBA':
                    # Create a white background
                    background = Image.new('RGB', image.size, 'white')
                    # Paste the image using alpha channel as mask
                    background.paste(image, mask=image.split()[3])
                    image = background
            
            # Enhance image if configured
            if self.config['operations']['enhance']:
                image = self._enhance_image(image)
            
            # Ensure final output is RGB
            if image.mode != 'RGB':
                image = image.convert('RGB')
                
            return image
            
        except Exception as e:
            logging.error(f"Error processing image: {str(e)}")
            raise

    def _enhance_image(self, image):
        """Apply enhancement operations to the image."""
        try:
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
                
            # Adjust contrast
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.2)
            
            # Adjust brightness
            enhancer = ImageEnhance.Brightness(image)
            image = enhancer.enhance(1.1)
            
            # Adjust sharpness
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.1)
            
            return image
            
        except Exception as e:
            logging.error(f"Error enhancing image: {str(e)}")
            raise

    def save_image(self, image, output_format='JPEG'):
        """Save image with proper format conversion."""
        try:
            # Ensure image is in RGB mode for JPEG
            if output_format.upper() == 'JPEG' and image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Create a buffer for the image
            img_buffer = io.BytesIO()
            
            # Save to buffer
            image.save(
                img_buffer,
                format=output_format,
                quality=self.config['quality']
            )
            
            img_buffer.seek(0)
            return img_buffer
            
        except Exception as e:
            logging.error(f"Error saving image: {str(e)}")
            raise

# Initialize Flask app
app = Flask(__name__)
processor = ProductImageProcessor()

# HTML template for the upload form
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Product Image Processor</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        .form-group {
            margin-bottom: 15px;
        }
        .checkbox-group {
            margin-bottom: 10px;
        }
        .submit-btn {
            background-color: #4CAF50;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        .submit-btn:hover {
            background-color: #45a049;
        }
        .error {
            color: red;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <h1>Product Image Processor</h1>
    <form action="/process" method="post" enctype="multipart/form-data">
        <div class="form-group">
            <label for="images">Select Images (multiple files allowed):</label><br>
            <input type="file" id="images" name="images" multiple accept="image/*" required>
        </div>
        
        <div class="form-group">
            <h3>Processing Options:</h3>
            <div class="checkbox-group">
                <input type="checkbox" id="resize" name="resize" checked>
                <label for="resize">Resize Images</label>
            </div>
            
            <div class="checkbox-group">
                <input type="checkbox" id="remove_background" name="remove_background">
                <label for="remove_background">Remove Background</label>
            </div>
            
            <div class="checkbox-group">
                <input type="checkbox" id="enhance" name="enhance" checked>
                <label for="enhance">Enhance Images</label>
            </div>
        </div>
        
        <input type="submit" value="Process Images" class="submit-btn">
    </form>
</body>
</html>
"""

@app.route('/imageprocess')
def index():
    """Render the upload form."""
    return render_template_string(HTML_TEMPLATE)

@app.route('/process', methods=['POST'])
def process_images():
    """Process uploaded images and return as zip file."""
    try:
        # Get processing options
        processor.config['operations'].update({
            'resize': 'resize' in request.form,
            'remove_background': 'remove_background' in request.form,
            'enhance': 'enhance' in request.form
        })

        # Check if files were uploaded
        if 'images' not in request.files:
            return 'No files uploaded', 400

        files = request.files.getlist('images')
        
        # Create a ZIP file in memory
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w') as zf:
            for file in files:
                if file.filename:
                    try:
                        # Read and process the image
                        img = Image.open(file.stream)
                        processed_img = processor.process_image(img)
                        
                        # Save processed image to buffer
                        img_buffer = processor.save_image(
                            processed_img,
                            processor.config['output_format']
                        )
                        
                        # Add to ZIP with timestamp in filename
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        filename = f"processed_{timestamp}_{file.filename}"
                        zf.writestr(filename, img_buffer.getvalue())
                        
                    except Exception as e:
                        logging.error(f"Error processing {file.filename}: {str(e)}")
                        continue

        # Prepare ZIP file for download
        memory_file.seek(0)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'processed_images_{timestamp}.zip'
        )

    except Exception as e:
        logging.error(f"Processing error: {str(e)}")
        return str(e), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')