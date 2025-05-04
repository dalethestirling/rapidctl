

def local_search(podman_session, container):
    local_images = podman_session.list_images()

    for image in local_images: 
        if container in image.tags:
            return image.short_id
    
    return None
