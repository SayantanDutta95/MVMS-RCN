import torch
import torch.nn as nn
from torch.nn import init
import torch.nn.functional as F
import numpy as np 
import os
from torch_radon import Radon


def initialize_weights(self):
    for m in self.modules():
        if isinstance(m, nn.Conv2d):
            init.xavier_normal_(m.weight)
            if m.bias is not None:
                init.constant_(m.bias, 0)
        elif isinstance(m, nn.BatchNorm2d):
            init.constant_(m.weight, 1)
            init.constant_(m.bias, 0)
        elif isinstance(m, nn.Linear):
            init.normal_(m.weight, 0, 0.01)
            init.constant_(m.bias, 0)


# define basic block of FISTA-Net
class  BasicBlock(nn.Module):
    """docstring for  BasicBlock"""

    def __init__(self, features):
        super(BasicBlock, self).__init__()

        self.Sp = nn.Softplus()

        self.conv_D = nn.Conv2d(1, features, (3,3), stride=1, padding=1)
        self.conv1_forward = nn.Conv2d(features, features, (3,3), stride=1, padding=1)
        self.conv2_forward = nn.Conv2d(features, features, (3,3), stride=1, padding=1)
        self.conv3_forward = nn.Conv2d(features, features, (3,3), stride=1, padding=1)
        self.conv4_forward = nn.Conv2d(features, features, (3,3), stride=1, padding=1)
        
        self.conv1_backward = nn.Conv2d(features, features, (3,3), stride=1, padding=1)
        self.conv2_backward = nn.Conv2d(features, features, (3,3), stride=1, padding=1)
        self.conv3_backward = nn.Conv2d(features, features, (3,3), stride=1, padding=1)
        self.conv4_backward = nn.Conv2d(features, features, (3,3), stride=1, padding=1)
        self.conv_G = nn.Conv2d(features, 1, (3,3), stride=1, padding=1)


    def forward(self, x, theta, sinogram, lambda_step, soft_thr):
        """
        x:              image from last stage, (batch_size, channel, height, width)
        theta:          angle vector for radon/iradon transform
        sinogram:       measured signogram of the target image
        lambda_step:    gradient descent step
        soft_thr:       soft-thresholding value
        """
        # rk block in the paper
        radon = Radon(x.shape[2], theta, det_count=729)
        sino_pred = radon.forward(x)
        filtered_sinogram = radon.filter_sinogram(sino_pred)
        X_fbp = radon.backprojection(filtered_sinogram - sinogram)

        x_input = x - self.Sp(lambda_step) * X_fbp
        
        # Dk block in the paper
        x_D = self.conv_D(x_input)

        # Hk block in the paper
        x = self.conv1_forward(x_D)
        x = F.relu(x)
        x = self.conv2_forward(x)
        x = F.relu(x)
        x = self.conv3_forward(x)
        x = F.relu(x)
        x_forward = self.conv4_forward(x)

        # soft-thresholding block
        x_st = torch.mul(torch.sign(x_forward), F.relu(torch.abs(x_forward) - self.Sp(soft_thr)))

        # Hk^hat block in the paper
        x = self.conv1_backward(x_st)
        x = F.relu(x)
        x = self.conv2_backward(x)
        x = F.relu(x)
        x = self.conv3_backward(x)
        x = F.relu(x)
        x_backward = self.conv4_backward(x)

        # Gk block in the paper
        x_G = self.conv_G(x_backward)

        # prediction output (skip connection); non-negative output
        x_pred = F.relu(x_input + x_G)

        # compute symmetry loss
        x = self.conv1_backward(x_forward)
        x = F.relu(x)
        x = self.conv2_backward(x)
        x = F.relu(x)
        x = self.conv3_backward(x)
        x = F.relu(x)
        x_D_est = self.conv4_backward(x)
        symloss = x_D_est - x_D

        return [x_pred, symloss, x_st]

class FISTANet(nn.Module):
    def __init__(self, LayerNo, num_feature):
        super(FISTANet, self).__init__()
        self.LayerNo = LayerNo

        onelayer = []
        self.bb = BasicBlock(num_feature)
        for i in range(LayerNo):
            onelayer.append(self.bb)

        self.fcs = nn.ModuleList(onelayer)
        self.fcs.apply(initialize_weights)
        
        # thresholding value
        self.w_theta = nn.Parameter(torch.Tensor([-0.5]))
        self.b_theta = nn.Parameter(torch.Tensor([-2]))
        # gradient step
        self.w_mu = nn.Parameter(torch.Tensor([-0.2]))
        self.b_mu = nn.Parameter(torch.Tensor([0.1]))
        # two-step update weight
        self.w_rho = nn.Parameter(torch.Tensor([0.5]))
        self.b_rho = nn.Parameter(torch.Tensor([0]))

        self.Sp = nn.Softplus()

    def forward(self, cond, x0, sinogram, theta, theta_label):
        """
        sinogram    : measured signal vector;
        x0          : initialized x with FBP
        """

        # initialize the result
        xold = x0
        y = xold 
        layers_sym = []     # for computing symmetric loss
        layers_st = []      # for computing sparsity constraints
        for i in range(self.LayerNo):
            theta_ = self.w_theta * i + self.b_theta
            mu_ = self.w_mu * i + self.b_mu
            [xnew, layer_sym, layer_st] = self.fcs[i](y, theta, sinogram, mu_, theta_)
            rho_ = (self.Sp(self.w_rho * i + self.b_rho) -  self.Sp(self.b_rho)) / self.Sp(self.w_rho * i + self.b_rho)
            y = xnew + rho_ * (xnew - xold) # two-step update
            xold = xnew
            layers_sym.append(layer_sym)
            layers_st.append(layer_st)

        return [xnew, layers_sym, layers_st]
