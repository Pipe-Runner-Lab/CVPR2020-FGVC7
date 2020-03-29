from torch import nn
import pretrainedmodels
import torchvision.models as models
from models.efficientnet import EfficientNet


class ModelFactory():
    def __init__(self):
        pass

    def get_model(self, model_name, num_classes, hyper_params=None, tuning_type='feature-extraction'):
        model = None

        if model_name == 'efficientnet-b7':
            print("[ Model : Efficientnet B7 ]")
            model = EfficientNet.from_pretrained()
            if tuning_type == 'feature-extraction':
                for param in model.parameters():
                    param.requires_grad = False
            num_ftrs = model._fc.in_features
            model._fc = nn.Sequential(
                nn.Linear(num_ftrs, num_classes),
                nn.Softmax(dim=1)
            )

            if hyper_params is not None:
                model._bn_mom = hyper_params['batch_norm_momentum']

        if model_name == 'densenet-161':
            print("[ Model : Densenet 161 ]")
            model = models.densenet161(pretrained=True)
            if tuning_type == 'feature-extraction':
                for param in model.parameters():
                    param.requires_grad = False
            num_ftrs = model.classifier.in_features
            model.classifier = nn.Sequential(
                nn.Linear(num_ftrs, num_classes),
                nn.Softmax(dim=1)
            )

        return model
