import copy
from typing import Optional, Tuple

import numpy as np
import torch
from torch_complex.tensor import ComplexTensor

from espnet.nets.pytorch_backend.frontends.feature_transform import LogMel
from espnet.nets.pytorch_backend.frontends.frontend import Frontend
from espnet2.asr.frontend.abs_frontend import AbsFrontend
from espnet2.layers.stft import Stft
from espnet2.utils.get_default_kwargs import get_defaut_kwargs


class DefaultFrontend(AbsFrontend):
    """Conventional frontend structure for ASR

    Stft -> WPE -> MVDR-Beamformer -> Power-spec -> Mel-Fbank -> CMVN
    """
    def __init__(
        self,
        stft_conf: dict = get_defaut_kwargs(Stft),
        frontend_conf: Optional[dict] = get_defaut_kwargs(Frontend),
        logmel_fbank_conf: dict = get_defaut_kwargs(LogMel),
    ):
        super().__init__()

        # Deepcopy (In general, dict shouldn't be used as default arg)
        stft_conf = copy.deepcopy(stft_conf)
        frontend_conf = copy.deepcopy(frontend_conf)
        logmel_fbank_conf = copy.deepcopy(logmel_fbank_conf)

        self.stft = Stft(**stft_conf)
        if frontend_conf is not None:
            self.frontend = Frontend(**frontend_conf)
        else:
            self.frontend = None

        self.logmel = LogMel(**logmel_fbank_conf)
        self.n_mels = logmel_fbank_conf['n_mels']

    def out_dim(self) -> int:
        return self.n_mels

    def forward(self, input: torch.Tensor, input_lengths: torch.Tensor) \
            -> Tuple[torch.Tensor, torch.Tensor]:
        # 1. Domain-conversion: e.g. Stft: time -> time-freq
        input_stft, feats_lens = self.stft(input, input_lengths)

        assert input_stft.dim() >= 4, input_stft.shape
        # "2" refers to the real/imag parts of Complex
        assert input_stft.shape[-1] == 2, input_stft.shape

        # Change torch.Tensor to ComplexTensor
        # input_stft: (..., F, T, 2) -> (..., F, T)
        input_stft = ComplexTensor(input_stft[..., 0], input_stft[..., 1])
        # input_stft: (..., F, T) -> (..., T, F)
        input_stft = input_stft.transpose(-1, -2)

        # 2. [Option] Speech enhancement
        if self.frontend is not None:
            assert isinstance(input_stft, ComplexTensor), type(input_stft)
            # input_stft: (Batch, [Channel,] Length, Freq)
            input_stft, _, mask = self.frontend(input_stft, feats_lens)

        # 3. [Multi channel case]: Select a channel
        if input_stft.dim() == 4:
            # h: (B, T, C, F) -> h: (B, T, F)
            if self.training:
                # Select 1ch randomly
                ch = np.random.randint(x.size(2))
                input_stft = input_stft[:, :, ch, :]
            else:
                # Use the first channel
                input_stft = input_stft[:, :, 0, :]

        # 4. STFT -> Power spectrum
        # h: ComplexTensor(B, T, F) -> torch.Tensor(B, T, F)
        input_power = input_stft.real ** 2 + input_stft.imag ** 2

        # 5. Feature transform e.g. Stft -> Log-Mel-Fbank
        # input_power: (Batch, [Channel,] Length, Freq)
        #       -> input_feats: (Batch, Length, Dim)
        input_feats, _ = self.logmel(input_power, feats_lens)

        return input_feats, feats_lens
