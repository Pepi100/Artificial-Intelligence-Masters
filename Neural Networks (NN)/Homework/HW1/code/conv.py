import torch
from torch import nn
import torch.nn.functional as F

from typing import Tuple
import numpy as np

def get_conv_weight_and_bias(
        filter_size: Tuple[int, int],
        num_groups: int,
        input_channels: int,
        output_channels: int,
        bias: bool
) -> Tuple[torch.Tensor, torch.Tensor]:
    # assert that num_filters is divisible by num_groups
    assert input_channels % num_groups == 0, "input channels must be divisible by groups number"
    # assert that num_channels is divisible by num_groups
    assert output_channels % num_groups == 0, "output channels must be divisible by groups number"
    input_channels = input_channels // num_groups

    # initialize the weight matrix
    weight_matrix = torch.randn(output_channels, input_channels, *filter_size)
    # initialize the bias vector
    if bias:
        bias_vector = torch.ones(output_channels)
    else:
        bias_vector = None
    return weight_matrix, bias_vector


class MyConvStub:
    def __init__(
            self,
            kernel_size: Tuple[int, int],
            num_groups: int,
            input_channels: int,
            output_channels: int,
            bias: bool,
            stride: int,
            dilation: int,
    ):
        self.weight, self.bias = get_conv_weight_and_bias(kernel_size, num_groups, input_channels, output_channels, bias)
        self.groups = num_groups
        self.stride = stride
        self.dilation = dilation


    def forward2D(self, x):
        return F.conv2d(
            x, self.weight, self.bias,
            stride=self.stride,
            dilation=self.dilation,
            groups=self.groups
        )

    def forward(self, x):
        b, c, h, w = x.shape
        out_c, in_g, kh, kw = self.weight.shape

        eh = self.dilation * (kh - 1) + 1
        ew = self.dilation * (kw - 1) + 1
        oh = (h - eh) // self.stride + 1
        ow = (w - ew) // self.stride + 1

        out = x.new_zeros((b, out_c, oh, ow))
        out_g = out_c // self.groups

        for i in range(oh):
            for j in range(ow):
                for g in range(self.groups):
                    ci = g * in_g
                    co = g * out_g

                    patch = x[:, ci:ci+in_g,
                        i*self.stride:i*self.stride+eh:self.dilation,
                        j*self.stride:j*self.stride+ew:self.dilation]

                    weights = self.weight[co:co+out_g]

                    out[:, co:co+out_g, i, j] = (
                        patch[:, None] * weights[None]
                    ).sum(dim=(2, 3, 4))

        if self.bias is not None:
            out += self.bias[None, :, None, None]

        return out
        


class MyFilterStub:
    def __init__(
            self,
            filter: torch.Tensor,
            input_channels: int,
    ):
        self.weight = filter
        self.input_channels = input_channels

    def forward2D(self, x):
        weight = self.weight[None, None].repeat(self.input_channels, 1, 1, 1)
        return F.conv2d(x, weight, groups=self.input_channels)

    def forward(self, x):
        b, c, h, w = x.shape
        kh, kw = self.weight.shape

        oh = h - kh + 1
        ow = w - kw + 1

        out = x.new_zeros((b, c, oh, ow))

        for i in range(oh):
            for j in range(ow):
                patch = x[:, :, i:i+kh, j:j+kw]
                out[:, :, i, j] = (patch * self.weight).sum(dim=(2, 3))

        return out
