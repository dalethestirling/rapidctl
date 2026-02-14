from typing import Optional, Dict, Any
import re
from urllib.parse import urlparse
import os.path

class CtlClient:
    """
    Class that defines and validates the required data that requires definition
    on the CTL client side of the stack.

    Once actions using this class are complete the CTL client should be ready
    to connect to the container layer and start command provisioning.
    """
    def __init__(self):
        self.container_repo: Optional[str] = None
        self.baseline_version: str = "1.0.0"
        self.client_version: str = "0.0.1"
        self.image_id: Optional[str] = None
        self.command_path: str = "/opt/rapidctl/cmd/"
    
    @property
    def container_version(self):
        """
         Function to provide an view of the container image tag

         Returns:
            str: Aggregrated version of the container repo path and version
        """
        return self._container_validator("%s:%s" % (self.container_repo, self.baseline_version))

    def _container_validator(self, container_image):
        """
         Sanitize a container image URL/name to prevent command injection and ensure valid format.
    
        Args:
            container_image (str): The container image URL or name to sanitize
        
        Returns:
            str: Sanitized container image string or None if invalid
        """
        # Return None if input is None or empty
        if not container_image or not isinstance(container_image, str):
            return None
    
        # Strip whitespace
        container_image = container_image.strip()
    
        # Check if the image contains a URL/registry part
        if '/' in container_image:
            # Parse as URL if it contains protocol
            if '://' in container_image:
                try:
                    parsed = urlparse(container_image)
                    # Validate the hostname
                    if not parsed.netloc:
                        return None
                
                    # Reconstruct the path part safely
                    path_parts = [part for part in parsed.path.split('/') if part]
                    safe_path = '/'.join(re.sub(r'[^a-zA-Z0-9._-]', '', part) for part in path_parts)
                
                    # Reconstruct the URL with sanitized components
                    return f"{parsed.scheme}://{parsed.netloc}/{safe_path}"
                except Exception:
                    return None
            else:
                # Handle registry/repo/image format (like docker.io/library/ubuntu)
                parts = container_image.split('/')
                safe_parts = []
            
                for part in parts:
                    # First part might be a domain name (registry)
                    if not safe_parts and '.' in part:
                    # Basic domain validation
                        if re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9\:\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\:\-]{0,61}[a-zA-Z0-9])?)*$', part):
                            safe_parts.append(part)
                        else:
                            return None
                    else:
                        # Repository and image name validation
                        safe_part = re.sub(r'[^a-zA-Z0-9._:@-]', '', part)
                        if safe_part:
                            safe_parts.append(safe_part)
            
                if safe_parts:
                    return '/'.join(safe_parts)
                return None
        else:
            # Simple image name (like "ubuntu" or "ubuntu:latest")
            image_parts = container_image.split(':')
        
            # Sanitize the image name
            safe_name = re.sub(r'[^a-zA-Z0-9._-]', '', image_parts[0])
        
            # Handle tag if present
            if len(image_parts) > 1:
                safe_tag = re.sub(r'[^a-zA-Z0-9._-]', '', image_parts[1])
                if safe_name and safe_tag:
                    return f"{safe_name}:{safe_tag}"
        
            if safe_name:
                return safe_name
        
            return None

