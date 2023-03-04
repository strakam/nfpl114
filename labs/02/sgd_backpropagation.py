#!/usr/bin/env python3
import argparse
import datetime
import os
import re
from typing import Tuple
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")  # Report only TF errors by default

import numpy as np
import tensorflow as tf

from mnist import MNIST

parser = argparse.ArgumentParser()
# These arguments will be set appropriately by ReCodEx, even if you change them.
parser.add_argument("--batch_size", default=50, type=int, help="Batch size.")
parser.add_argument("--debug", default=False, action="store_true", help="If given, run functions eagerly.")
parser.add_argument("--epochs", default=10, type=int, help="Number of epochs.")
parser.add_argument("--hidden_layer", default=100, type=int, help="Size of the hidden layer.")
parser.add_argument("--learning_rate", default=0.1, type=float, help="Learning rate.")
parser.add_argument("--recodex", default=False, action="store_true", help="Evaluation in ReCodEx.")
parser.add_argument("--seed", default=42, type=int, help="Random seed.")
parser.add_argument("--threads", default=1, type=int, help="Maximum number of threads to use.")
# If you add more arguments, ReCodEx will keep them with your default values.


class Model(tf.Module):
    def __init__(self, args: argparse.Namespace) -> None:
        self._args = args

        self._W1 = tf.Variable(
            tf.random.normal([MNIST.W * MNIST.H * MNIST.C, args.hidden_layer], stddev=0.1, seed=args.seed),
            trainable=True,
        )
        self._b1 = tf.Variable(tf.zeros([args.hidden_layer]), trainable=True)

        # TODO: Create variables:
        # - _W2, which is a trainable Variable of size [args.hidden_layer, MNIST.LABELS],
        #   initialized to `tf.random.normal` value with stddev=0.1 and seed=args.seed,
        # - _b2, which is a trainable Variable of size [MNIST.LABELS] initialized to zeros
        self._W2 = tf.Variable(
            tf.random.normal([args.hidden_layer, MNIST.LABELS], stddev=0.1, seed=args.seed),
            trainable=True,
        )
        self._b2 = tf.Variable(tf.zeros([MNIST.LABELS]), trainable=True)

    def predict(self, inputs: tf.Tensor) -> tf.Tensor:
        # TODO: Define the computation of the network. Notably:
        # - start by reshaping the inputs to shape [inputs.shape[0], -1].
        #   The -1 is a wildcard which is computed so that the number
        #   of elements before and after the reshape fits.
        # - then multiply the inputs by `self._W1` and then add `self._b1`
        # - apply `tf.nn.tanh`
        # - multiply the result by `self._W2` and then add `self._b2`
        # - finally apply `tf.nn.softmax` and return the result
        inputs = tf.reshape(inputs, [inputs.shape[0], -1])
        hidden_layer = tf.nn.tanh(tf.matmul(inputs, self._W1) + self._b1)
        output = tf.nn.softmax(tf.matmul(hidden_layer, self._W2) + self._b2)
        return output

    def train_epoch(self, dataset: MNIST.Dataset) -> None:
        for batch in dataset.batches(self._args.batch_size):
            # The batch contains
            # - batch["images"] with shape [?, MNIST.H, MNIST.W, MNIST.C]
            # - batch["labels"] with shape [?]
            # Size of the batch is `self._args.batch_size`, except for the last, which
            # might be smaller.

            # The tf.GradientTape is used to record all operations inside the with block.
            with tf.GradientTape() as tape:
                # TODO: Compute the predicted probabilities of the batch images using `self.predict`
                probabilities = self.predict(batch["images"])

                # TODO: Manually compute the loss:
                # - For every batch example, the loss is the categorical crossentropy of the
                #   predicted probabilities and the gold label. To compute the crossentropy, you can
                #   - either use `tf.one_hot` to obtain one-hot encoded gold labels,
                #   - or use `tf.gather` with `batch_dims=1` to "index" the predicted probabilities.
                # - Finally, compute the average across the batch examples.
                one_hotted = tf.one_hot(batch["labels"], MNIST.LABELS)
                cce = tf.keras.losses.CategoricalCrossentropy(one_hotted, probabilities)  
                print(cce)
                loss = tf.reduce_mean(tf.keras.losses.categorical_crossentropy(one_hotted, probabilities))

            # We create a list of all variables. Note that a `tf.Module` automatically
            # tracks owned variables, so we could also use `self.trainable_variables`
            # (or even `self.variables`, which is useful for loading/saving).
            variables = [self._W1, self._b1, self._W2, self._b2]

            # TODO: Compute the gradient of the loss with respect to variables using
            # backpropagation algorithm via `tape.gradient`
            gradients = tape.gradient(loss, variables)

            for variable, gradient in zip(variables, gradients):
                # TODO: Perform the SGD update with learning rate `self._args.learning_rate`
                # for the variable and computed gradient. You can modify
                # variable value with `variable.assign` or in this case the more
                # efficient `variable.assign_sub`.
                variable.assign_sub(self._args.learning_rate * gradient)

    def evaluate(self, dataset: MNIST.Dataset) -> float:
        # Compute the accuracy of the model prediction
        correct = 0
        for batch in dataset.batches(self._args.batch_size):
            # TODO: Compute the probabilities of the batch images
            probabilities = self.predict(batch["images"])
            predictions = tf.argmax(probabilities, axis=1)
            # TODO: Evaluate how many batch examples were predicted
            # correctly and increase `correct` variable accordingly.
            correct += np.sum(predictions == batch["labels"])

        return correct / dataset.size


def main(args: argparse.Namespace) -> Tuple[float, float]:
    # Set the random seed and the number of threads.
    tf.keras.utils.set_random_seed(args.seed)
    tf.config.threading.set_inter_op_parallelism_threads(args.threads)
    tf.config.threading.set_intra_op_parallelism_threads(args.threads)
    if args.debug:
        tf.config.run_functions_eagerly(True)
        tf.data.experimental.enable_debug_mode()

    # Create logdir name
    args.logdir = os.path.join("logs", "{}-{}-{}".format(
        os.path.basename(globals().get("__file__", "notebook")),
        datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S"),
        ",".join(("{}={}".format(re.sub("(.)[^_]*_?", r"\1", k), v) for k, v in sorted(vars(args).items())))
    ))

    # Load data
    mnist = MNIST()

    # Create the TensorBoard writer
    writer = tf.summary.create_file_writer(args.logdir, flush_millis=10 * 1000)

    # Create the model
    model = Model(args)

    for epoch in range(args.epochs):
        # TODO: Run the `train_epoch` with `mnist.train` dataset
        model.train_epoch(mnist.train)
        # TODO: Evaluate the dev data using `evaluate` on `mnist.dev` dataset
        accuracy = model.evaluate(mnist.dev)
        print("Dev accuracy after epoch {} is {:.2f}".format(epoch + 1, 100 * accuracy), flush=True)
        with writer.as_default(step=epoch + 1):
            tf.summary.scalar("dev/accuracy", 100 * accuracy)

    # TODO: Evaluate the test data using `evaluate` on `mnist.test` dataset
    test_accuracy = model.evaluate(mnist.test)
    print("Test accuracy after epoch {} is {:.2f}".format(epoch + 1, 100 * test_accuracy), flush=True)
    with writer.as_default(step=epoch + 1):
        tf.summary.scalar("test/accuracy", 100 * test_accuracy)

    # Return dev and test accuracies for ReCodEx to validate.
    return accuracy, test_accuracy


if __name__ == "__main__":
    args = parser.parse_args([] if "__file__" not in globals() else None)
    main(args)
