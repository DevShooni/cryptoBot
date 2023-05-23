import numpy as np
import random
from tensorflow.python.keras.models import Sequential, load_model
from tensorflow.python.keras.layers import Dense
from tensorflow.python.keras.optimizer_v2.adam import Adam


class DQN:
    def __init__(self, state_size, action_size, learning_rate=0.001, gamma=0.99,
                 epsilon=1.0, epsilon_decay=0.995, epsilon_min=0.01, memory_size=10000):
        self.state_size = state_size
        self.action_size = action_size
        self.learning_rate = learning_rate
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.epsilon_min = epsilon_min
        self.memory = []
        self.memory_size = memory_size

        self.model = self.build_model()

    def build_model(self):
        model = Sequential()
        model.add(Dense(24, input_dim=self.state_size, activation='relu'))
        model.add(Dense(24, activation='relu', input_shape=(self.state_size,)))
        model.add(Dense(self.action_size, activation='linear'))
        model.compile(loss='mse', optimizer=Adam(lr=self.learning_rate))
        return model

    def remember(self, state, action, reward, next_state, done):
        if len(self.memory) >= self.memory_size:
            self.memory.pop(0)
        self.memory.append((state, action, reward, next_state, done))

    def act(self, state):
        if np.random.rand() <= self.epsilon:
            return random.randrange(self.action_size)
        state = np.array(state)
        action = np.argmax(self.model.predict(state))
        return action

    def replay(self, batch_size):
        # Sample a minibatch from the memory
        minibatch = random.sample(self.memory, min(len(self.memory), batch_size))

        for state, action, reward, next_state, done in minibatch:
            # Calculate the target Q-value
            target = reward
            if not done:
                next_state = np.array(next_state)
                target += self.gamma * np.amax(self.model.predict(next_state))

            # Update the Q-value for the chosen action
            state = np.array(state)
            target_f = self.model.predict(state)
            target_f[0][action] = target

            # Train the model on the state and target Q-value
            self.model.fit(state, target_f, epochs=1, verbose=0)

        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

    def save_model(self):
        self.model.save("G:\\PythonProjects\\TradeBot\\crypto\\cryptoDQN\\model.h5")

    def load_model(self):
        return load_model("G:\\PythonProjects\\TradeBot\\crypto\\cryptoDQN\\model.h5")
