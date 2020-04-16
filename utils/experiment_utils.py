import torch
from os import (makedirs, path)
from shutil import rmtree
import pandas as pd
import math
from utils.regression_utils import covert_to_classification
from utils.kaggle_metric import (roc_auc_score_generator)
from utils.print_util import cprint
from utils.telegram_update import publish


def accuracy_generator(output_list, target_list):
    acc = torch.argmax(target_list, dim=1).eq(
        torch.argmax(output_list, dim=1))
    return 1.0 * torch.sum(acc.int()).item() / output_list.size()[0]


class ExperimentHelper:
    def __init__(self, experiment_name, freq=None, tb_writer=None, overwrite=False,):
        if path.exists(path.join('results', experiment_name)) == False:
            makedirs(path.join('results', experiment_name))
        else:
            if overwrite:
                cprint("[ <", experiment_name,
                       "> output exists - Overwriting! ]", type="warn")
                rmtree(path.join('results', experiment_name))
                makedirs(path.join('results', experiment_name))
            else:
                cprint("[ <", experiment_name,
                       "> output exists - Manual deletion needed ]", type="warn")
                exit()

        self.experiment_name = experiment_name
        self.best_val_loss = float('inf')
        self.best_val_roc = 0
        self.result = {
            "config": experiment_name,
            "best_val_loss": self.best_val_loss,
            "val_acc": None,
            "train_loss": None,
            "train_acc": None,
            "val_roc": None,
            "train_roc": None,
            "epoch": None
        }
        self.tb_writer = tb_writer
        self.freq = freq
        self.progress_loss = False
        self.progress_roc = False

    def should_trigger(self, i):
        if self.freq:
            return (i + 1) % self.freq == 0
        return True

    def is_progress(self):
        return (self.progress_loss or self.progress_roc)

    def save_checkpoint(self, state_dict):
        if self.progress_loss:
            torch.save(
                state_dict,
                path.join('results', self.experiment_name, 'weights_loss.pth')
            )
        if self.progress_roc:
            torch.save(
                state_dict,
                path.join('results', self.experiment_name, 'weights_roc.pth')
            )

    def validate(self, pred_type, num_classes, loss_fn, val_output_list, val_target_list, train_output_list, train_target_list, epoch):
        with torch.no_grad():
            # loss calculation
            val_loss = loss_fn(
                val_output_list, val_target_list).item()
            train_loss = loss_fn(
                train_output_list, train_target_list).item()

            if pred_type == 'regression' or pred_type == 'mixed':
                train_output_list = covert_to_classification(
                    train_output_list,
                    num_classes,
                )
                val_output_list = covert_to_classification(
                    val_output_list,
                    num_classes,
                )

            val_acc = accuracy_generator(val_output_list, val_target_list)
            train_acc = accuracy_generator(
                train_output_list, train_target_list)

            val_roc = roc_auc_score_generator(val_output_list, val_target_list)
            train_roc = roc_auc_score_generator(
                train_output_list, train_target_list)

            # saving results to csv
            df = pd.DataFrame(
                [[epoch + 1, val_loss, train_loss, val_acc, train_acc, val_roc, train_roc]])
            result_path = path.join(
                'results', self.experiment_name, 'result.csv')

            if not path.isfile(result_path):
                df.to_csv(
                    result_path,
                    header=[
                        "epoch", "Loss ( Val )", "Loss ( Train )", "Accuracy ( Val )", "Accuracy ( Train )", "ROC ( Val )", "ROC ( Train )"
                    ],
                    index=False
                )
            else:
                df.to_csv(result_path, mode='a', header=False, index=False)

            # creating tensorboard events
            if self.tb_writer is not None:
                self.tb_writer.add_scalar('Loss/Train', train_loss, epoch)
                self.tb_writer.add_scalar('Loss/Validation', val_loss, epoch)
                self.tb_writer.add_scalar('Accuracy/Train', train_acc, epoch)
                self.tb_writer.add_scalar(
                    'Accuracy/Validation', val_acc, epoch)
                self.tb_writer.add_scalar('ROC/Train', train_roc, epoch)
                self.tb_writer.add_scalar('ROC/Validation', val_roc, epoch)

            # storing loss for check
            if self.best_val_loss >= val_loss:
                self.best_val_loss = val_loss
                self.progress_loss = True

                # update dict for publishing
                self.result["best_val_loss"] = val_loss
                self.result["val_acc"] = val_acc
                self.result["train_loss"] = train_loss
                self.result["train_acc"] = train_acc
                self.result["val_roc"] = val_roc
                self.result["train_roc"] = train_roc
                self.result["epoch"] = epoch
            else:
                self.progress_loss = False

            # storing roc for check
            if self.best_val_roc < val_roc:
                self.best_val_roc = val_roc
                self.progress_roc = True
            else:
                self.progress_roc = False

            return (val_loss, train_loss, val_acc, train_acc, val_roc, train_roc)

    def publish(self):
        publish(self.result)
