function PS=PNSR(img_before,img_after)
%��ֵ����Ⱥ;������%Peak Signal to Noise Ratio(PSNR)
img_ref=double(img_before);
img_den=double(img_after);%��ֵ����Ⱥ;������%Peak Signal to Noise Ratio(PSNR)?
width = size(img_ref,2); 
heigh = size(img_ref,1); 
if( width ~= size(img_den,2) || heigh ~= size(img_den,1) ) 
    disp('Please check the input image have the same size'); 
    return 
end 
[a,b]=size(img_ref); 
XX2=double(img_ref) - double(img_den); 
mse_value2 = sum(sum( XX2.^2 ))/(a*b); 
PS = 10*log10( 255*255 / mse_value2 ); %get pnsr ?
% fprintf('��ֵ�����(PSNR)��%6.4f',PS);
% fprintf('���������%6.4f',mse_value2);
