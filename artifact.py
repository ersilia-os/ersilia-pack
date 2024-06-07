class ModelArtifact(object):

    def __init__(self, loaded_model):
        self.loaded_model = loaded_model

    def run(self, data):
        return data