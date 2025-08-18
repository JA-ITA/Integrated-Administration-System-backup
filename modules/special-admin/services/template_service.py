"""
Template service for certificate template management
Handles Handlebars compilation and HTML preview generation
"""
import json
import base64
import re
from typing import Dict, Any, Optional
from jinja2 import Environment, BaseLoader, Template
import logging

logger = logging.getLogger(__name__)

class TemplateService:
    """Service for managing certificate templates"""
    
    def __init__(self):
        # Initialize Jinja2 environment (as Handlebars alternative)
        self.jinja_env = Environment(loader=BaseLoader())
        
        # Default sample data for preview
        self.default_sample_data = {
            "candidate_name": "John Doe",
            "certificate_type": "Special Driving License",
            "issue_date": "December 15, 2024",
            "expiry_date": "December 15, 2027",
            "license_number": "SDL-2024-001234",
            "test_score": "85%",
            "issuing_authority": "International Transport Authority",
            "qr_code_data": "https://verify.itadias.com/SDL-2024-001234",
            "seal_image": "/images/official-seal.png",
            "signature_image": "/images/authority-signature.png"
        }
    
    async def compile_template(self, hbs_content: str, css_content: Optional[str] = None, 
                             sample_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Compile Handlebars template and generate preview"""
        try:
            # Use provided sample data or default
            data = sample_data or self.default_sample_data
            
            # Convert Handlebars syntax to Jinja2 (basic conversion)
            jinja_content = self._convert_handlebars_to_jinja(hbs_content)
            
            # Create Jinja2 template
            template = self.jinja_env.from_string(jinja_content)
            
            # Render template with sample data
            rendered_html = template.render(**data)
            
            # Wrap with CSS if provided
            if css_content:
                full_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Certificate Preview</title>
    <style>
        {css_content}
    </style>
</head>
<body>
    {rendered_html}
</body>
</html>
"""
            else:
                full_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Certificate Preview</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .certificate {{ border: 2px solid #000; padding: 20px; text-align: center; }}
    </style>
</head>
<body>
    {rendered_html}
</body>
</html>
"""
            
            return {
                "success": True,
                "preview_html": full_html,
                "compiled_template": rendered_html,
                "original_hbs": hbs_content,
                "jinja_template": jinja_content
            }
            
        except Exception as e:
            logger.error(f"Template compilation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "preview_html": f"<div>Template Error: {str(e)}</div>"
            }
    
    def _convert_handlebars_to_jinja(self, hbs_content: str) -> str:
        """Convert basic Handlebars syntax to Jinja2"""
        # Basic conversion - replace {{var}} with {{var}}
        # Jinja2 and Handlebars have similar syntax for basic variables
        
        # Convert Handlebars helpers to Jinja2 filters/functions
        jinja_content = hbs_content
        
        # Convert {{#if}} blocks to {% if %}
        import re
        
        # Replace {{#if condition}} with {% if condition %}
        jinja_content = re.sub(r'\{\{#if\s+([^}]+)\}\}', r'{% if \1 %}', jinja_content)
        jinja_content = re.sub(r'\{\{/if\}\}', r'{% endif %}', jinja_content)
        
        # Replace {{#each}} with {% for %}
        jinja_content = re.sub(r'\{\{#each\s+([^}]+)\}\}', r'{% for item in \1 %}', jinja_content)
        jinja_content = re.sub(r'\{\{/each\}\}', r'{% endfor %}', jinja_content)
        
        # Replace {{#unless}} with {% if not %}
        jinja_content = re.sub(r'\{\{#unless\s+([^}]+)\}\}', r'{% if not \1 %}', jinja_content)
        jinja_content = re.sub(r'\{\{/unless\}\}', r'{% endif %}', jinja_content)
        
        return jinja_content
    
    async def generate_handlebars_template(self, json_config: Dict[str, Any]) -> str:
        """Generate Handlebars template from drag-drop configuration"""
        try:
            # Extract configuration
            elements = json_config.get("elements", [])
            layout = json_config.get("layout", {})
            
            # Start building template
            template_parts = []
            
            # Add container div
            container_style = self._build_style_string(layout.get("container", {}))
            template_parts.append(f'<div class="certificate-container" style="{container_style}">')
            
            # Process each element
            for element in elements:
                element_html = self._generate_element_html(element)
                template_parts.append(element_html)
            
            template_parts.append('</div>')
            
            return '\n'.join(template_parts)
            
        except Exception as e:
            logger.error(f"Template generation failed: {e}")
            raise
    
    def _generate_element_html(self, element: Dict[str, Any]) -> str:
        """Generate HTML for a single element"""
        element_type = element.get("type", "text")
        content = element.get("content", "")
        style = self._build_style_string(element.get("style", {}))
        position = element.get("position", {})
        
        # Build positioning style
        position_style = ""
        if position:
            position_style = f"position: absolute; left: {position.get('x', 0)}px; top: {position.get('y', 0)}px;"
        
        full_style = f"{style} {position_style}".strip()
        
        if element_type == "text":
            return f'<div style="{full_style}">{content}</div>'
        elif element_type == "field":
            field_name = element.get("field", "default")
            return f'<div style="{full_style}">{{{{ {field_name} }}}}</div>'
        elif element_type == "image":
            src = element.get("src", "")
            alt = element.get("alt", "")
            return f'<img src="{src}" alt="{alt}" style="{full_style}" />'
        elif element_type == "qr_code":
            return f'<div class="qr-code" style="{full_style}">{{{{ qr_code_data }}}}</div>'
        else:
            return f'<div style="{full_style}">{content}</div>'
    
    def _build_style_string(self, style_dict: Dict[str, Any]) -> str:
        """Build CSS style string from dictionary"""
        if not style_dict:
            return ""
        
        style_parts = []
        for key, value in style_dict.items():
            # Convert camelCase to kebab-case
            css_key = re.sub(r'([A-Z])', r'-\1', key).lower()
            style_parts.append(f"{css_key}: {value}")
        
        return "; ".join(style_parts)
    
    async def get_default_template_config(self) -> Dict[str, Any]:
        """Get default template configuration for the designer"""
        return {
            "elements": [
                {
                    "type": "text",
                    "content": "CERTIFICATE OF COMPLETION",
                    "position": {"x": 100, "y": 50},
                    "style": {
                        "fontSize": "24px",
                        "fontWeight": "bold",
                        "textAlign": "center",
                        "color": "#000"
                    }
                },
                {
                    "type": "field",
                    "field": "candidate_name",
                    "content": "Candidate Name",
                    "position": {"x": 100, "y": 150},
                    "style": {
                        "fontSize": "18px",
                        "textAlign": "center"
                    }
                },
                {
                    "type": "field",
                    "field": "issue_date",
                    "content": "Issue Date",
                    "position": {"x": 100, "y": 250},
                    "style": {
                        "fontSize": "14px"
                    }
                },
                {
                    "type": "qr_code",
                    "position": {"x": 500, "y": 300},
                    "style": {
                        "width": "100px",
                        "height": "100px"
                    }
                }
            ],
            "layout": {
                "container": {
                    "width": "800px",
                    "height": "600px",
                    "border": "2px solid #000",
                    "position": "relative",
                    "backgroundColor": "#fff"
                }
            }
        }