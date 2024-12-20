from BaseEnv import BaseClass
import tensorflow as tf
from tensorflow.keras.layers import SimpleRNN, LSTM, Dense, Dropout, TimeDistributed, BatchNormalization
from tensorflow.keras.models import Sequential
import pandas as pd
from sklearn.metrics import mean_squared_error
import numpy as np
import matplotlib.pyplot as plt

import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'


class RNNClass(BaseClass):

    def __init__(self,
        feature_steps: int = 10,
        target_steps: int = 1,
        batchnormalization: bool = False,
        layers_RNN: int = 2,
        layers_LSTM: int = 2
    ):  
        super().__init__(feature_steps = feature_steps, target_steps = target_steps)
        self.models = {}
        self.bn = batchnormalization
        self.layers = {SimpleRNN: layers_RNN, LSTM: layers_LSTM}
        self.models_function_name = {SimpleRNN: self.rnn_dense_model, LSTM: self.lstm_model}
        self.models_name_str = {SimpleRNN: "SimpleRNN", LSTM: "LSTM"}
        self.train_series = {}
        self.train_pred = {}
        self.valid_pred = {}
        self.test_pred = {}
        self.test_pred_rescaled = {}
        self.train_errors = {}
        self.valid_errors = {}
        self.test_errors = {}
        self.y_pred_prc = {}
        self.y_test_prc = {}
        self.restored_prices = {}
        self.test_dates = {}
        self.history = {}
        for name in self.tickers.groups.keys():
            self.train_series[name] = np.concatenate( (self.y_train[name],self.y_valid[name],self.y_test[name]), axis=0)
            self.models[name] = dict()
            self.train_pred[name] = {SimpleRNN: [], LSTM: []}
            self.valid_pred[name] = {SimpleRNN: [], LSTM: []}
            self.test_pred[name] = {SimpleRNN: [], LSTM: []}
            self.test_pred_rescaled[name] = {SimpleRNN: [], LSTM: []}
            self.train_errors[name] = {SimpleRNN: [], LSTM: []}
            self.valid_errors[name] = {SimpleRNN: [], LSTM: []}
            self.test_errors[name] = {SimpleRNN: [], LSTM: []}
            self.y_pred_prc[name] = {SimpleRNN: [], LSTM: []}
            self.y_test_prc[name] = {SimpleRNN: [], LSTM: []}
            self.restored_prices[name] = {SimpleRNN: [], LSTM: []}
            self.test_dates[name] = {SimpleRNN: [], LSTM: []}
            self.history[name] = {}

    def Prediction(self,
        model
    ):
        for name in self.tickers.groups.keys():
            self.reset_session()
            n_train = len(self.X_train[name])
            n_valid = len(self.X_valid[name])
            n_test = len(self.X_test[name])

            input_shape = (self.X_train[name].shape[1], 1)
            output_units = self.y_train[name].shape[1] if len(self.y_train[name].shape) > 1 else 1

            if model in [SimpleRNN, LSTM]:
                m = self.models_function_name[model](input_shape=input_shape, output_units=output_units, layers = self.layers[model])
                m.compile(loss="mse", optimizer="nadam")
            else:
                raise TypeError("model must be SimpleRNN or LSTM")
            

            early_stopping_cb = tf.keras.callbacks.EarlyStopping(patience=200,
                                                              min_delta=0.01,
                                                              restore_best_weights=True)
            
            self.history[name][model] = m.fit(self.X_train[name][..., np.newaxis], self.y_train[name][..., np.newaxis], epochs=50,
                                              validation_data=(self.X_valid[name][..., np.newaxis], self.y_valid[name][..., np.newaxis]),
                                              callbacks=[early_stopping_cb], verbose=0)

            #pd.DataFrame(run.history).iloc[-11:]

            self.train_pred[name][model] = m.predict(self.X_train[name])
            self.valid_pred[name][model] = m.predict(self.X_valid[name])
            self.test_pred[name][model] = m.predict(self.X_test[name])

            self.train_errors[name][model] = mean_squared_error(self.y_train[name], self.train_pred[name][model])
            self.valid_errors[name][model] = mean_squared_error(self.y_valid[name], self.valid_pred[name][model])
            self.test_errors[name][model] = mean_squared_error(self.y_test[name], self.test_pred[name][model])

            self.y_predict_rescaled(model,name,n_test)
            self.test_dates[name][model] = self.dates[-n_test:]

            self.models[name][model] = m

    def rnn_dense_model(self,
        input_shape,
        output_units,
        layers
    ):
        model = Sequential()
        
        for i in range(layers):
            model.add(SimpleRNN(units=64, activation='relu', input_shape=input_shape, return_sequences=True))
            model.add(Dropout(0.2))        

            model.add(TimeDistributed(Dense(units=32, activation='relu')))

        model.add(SimpleRNN(units=64, activation='relu', return_sequences=False))
        model.add(Dropout(0.2))
        
        model.add(Dense(units=64, activation='relu'))

        if self.bn:
            model.add(BatchNormalization())

        model.add(Dense(units=32, activation='relu'))
        
        model.add(Dense(units=output_units))
        return model

    def lstm_model(self,
        input_shape,
        output_units,
        layers
    ):
        model = Sequential()

        for i in range(layers):
            model.add(LSTM(units=64, input_shape=input_shape, return_sequences=True))
            model.add(Dropout(0.2))
        
        model.add(LSTM(units=64, return_sequences=False))
        
        model.add(Dense(units=output_units))
        
        return model

    def reset_session(self,
            seed=42
        ):
            tf.random.set_seed(seed)
            np.random.seed(seed)
            tf.keras.backend.clear_session()

    def VisualizationRNN(self,
        model,
        plot: bool = False,
        logdiff: bool = True
    ):
        if model not in [SimpleRNN,LSTM]:
            raise TypeError("model must be SimpleRNN or LSTM")
        else:
            self.Visualization(model=model,plot=plot,logdiff=logdiff)