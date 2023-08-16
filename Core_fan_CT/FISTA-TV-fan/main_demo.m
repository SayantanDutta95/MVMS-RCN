clc;close all; clear;
%% load data
addpath('.\TV'); 
addpath('.\npy2matlab');

sample = readNPY('.\data\test_images.npy');
Xgt = squeeze(sample(3,1,:,:));
img_size = size(Xgt);

% generate projection data from phantom using radon transform
Np = 720;
theta = (0:Np-1)*180/Np;
y = radon(Xgt, theta, 739);    % 739 pixels; 720 projection views; Mayo CT
figure; imagesc(Xgt);title('Ground Truth')

% downsample projection data from full-view CT
ds_factor = 12;
y_ds = y(:,1:ds_factor:end);
theta_ds = theta(1:ds_factor:end);
X_0 = iradon(y_ds,theta_ds);
X_0 = imresize(X_0, size(Xgt));
figure; imagesc(X_0); title('FBP');

%% 

% Iterative Total Varaition using FISTA
% 'iso'--> isotropic TV
% 'l1' --> l1-based, anisotropic TV
pars.tv = 'iso';
pars.MAXITER = 200;
pars.fig = 0;
X_fista_tv = tv_fista(y_ds,theta_ds,img_size, 0.05,-Inf,Inf,pars);

figure; 
imagesc(X_fista_tv); truesize([500 500]);
colormap(gray); caxis([0 0.6]);
axis off
