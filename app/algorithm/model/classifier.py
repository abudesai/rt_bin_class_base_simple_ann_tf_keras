import numpy as np, pandas as pd
import joblib
import sys
import os, warnings

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"  # or any {'0', '1', '2'}
warnings.filterwarnings("ignore")


import tensorflow as tf
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input, Dense
from tensorflow.keras.regularizers import l2, l1_l2
from tensorflow.keras.optimizers import SGD, Adam
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau, Callback
from tensorflow.keras.losses import BinaryCrossentropy


model_params_fname = "model_params.save"
model_wts_fname = "model_wts.save"
history_fname = "history.json"

MODEL_NAME = "bin_class_base_simple_ANN_tf_keras"

COST_THRESHOLD = float("inf")


class InfCostStopCallback(Callback):
    def on_epoch_end(self, epoch, logs={}):
        loss_val = logs.get("loss")
        if loss_val == COST_THRESHOLD or tf.math.is_nan(loss_val):
            # print("Cost is inf, so stopping training!!")
            self.model.stop_training = True


class Classifier:
    def __init__(self, D, l1_reg=1e-3, l2_reg=1e-1, lr=1e-3, **kwargs) -> None:
        self.D = D
        self.l1_reg = np.float(l1_reg)
        self.l2_reg = np.float(l2_reg)
        self.lr = lr

        self.model = self.build_model()
        self.model.compile(
            loss=BinaryCrossentropy(),
            # optimizer=Adam(learning_rate=self.lr),
            optimizer=SGD(learning_rate=self.lr),
            metrics=["accuracy"],
        )

    def build_model(self):

        M1 = max(2, int(self.D * 1.5))
        M2 = 4

        reg = l1_l2(l1=self.l1_reg, l2=self.l2_reg)
        input_ = Input(self.D)
        x = input_
        x = Dense(M1, activity_regularizer=reg, activation="relu")(x)
        x = Dense(M2, activity_regularizer=reg, activation="relu")(x)
        x = Dense(1, activity_regularizer=reg, activation='sigmoid')(x)
        output_ = x
        model = Model(input_, output_)
        # model.summary()
        return model

    def fit(
        self,
        train_X,
        train_y,
        valid_X=None,
        valid_y=None,
        batch_size=256,
        epochs=100,
        verbose=0,
    ):

        if valid_X is not None and valid_y is not None:
            early_stop_loss = "val_loss"
            validation_data = [valid_X, valid_y]
        else:
            early_stop_loss = "loss"
            validation_data = None

        early_stop_callback = EarlyStopping(
            monitor=early_stop_loss, min_delta=1e-3, patience=5
        )
        infcost_stop_callback = InfCostStopCallback()

        history = self.model.fit(
            x=train_X,
            y=train_y,
            batch_size=batch_size,
            validation_data=validation_data,
            epochs=epochs,
            verbose=verbose,
            shuffle=True,
            callbacks=[early_stop_callback, infcost_stop_callback],
        )
        return history

    def predict(self, X, verbose=False):
        preds = self.model.predict(X, verbose=verbose)
        return preds

    def summary(self):
        self.model.summary()

    def evaluate(self, x_test, y_test):
        """Evaluate the model and return the loss and metrics"""
        if self.model is not None:
            return self.model.evaluate(x_test, y_test, verbose=0)

    def save(self, model_path):
        model_params = {
            "D": self.D,
            "l1_reg": self.l1_reg,
            "l2_reg": self.l2_reg,
            "lr": self.lr,
        }
        joblib.dump(model_params, os.path.join(model_path, model_params_fname))
        self.model.save_weights(os.path.join(model_path, model_wts_fname))

    @classmethod
    def load(cls, model_path):
        # print(model_params_fname, model_wts_fname)
        model_params = joblib.load(os.path.join(model_path, model_params_fname))
        logreg_model = cls(**model_params)
        logreg_model.model.load_weights(
            os.path.join(model_path, model_wts_fname)
        ).expect_partial()
        return logreg_model


def save_model(model, model_path):
    model.save(model_path)


def load_model(model_path):
    try:
        model = Classifier.load(model_path)
    except:
        raise Exception(
            f"""Error loading the trained {MODEL_NAME} model. 
            Do you have the right trained model in path: {model_path}?"""
        )
    return model


def save_training_history(history, f_path):
    hist_df = pd.DataFrame(history.history)
    hist_json_file = os.path.join(f_path, history_fname)
    with open(hist_json_file, mode="w") as f:
        hist_df.to_json(f)


def get_data_based_model_params(data):
    """
    Set any model parameters that are data dependent.
    For example, number of layers or neurons in a neural network as a function of data shape.
    """
    return {"D": data.shape[1]}
