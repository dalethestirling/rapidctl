import rapidctl.cli.tasks

def find_container(podman_session, container):
    image = rapidctl.cli.tasks.local_search(podman_session, container)

    return image 

def pull_container(podman_session, container):
    print(container)
    image = podman_session.pull_image(container)

    return image
