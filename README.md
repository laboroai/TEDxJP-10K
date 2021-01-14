# TEDxJP-10K ASR Evaluation Dataset

## Overview
TEDxJP-10k is a Japanese speech dataset for ASR evalation built from Japanese TEDx videos and their subtitles. While test sets of ASR corpora are usually developed as subsets of entire data, which results in similar characteristics between the train and test sets, this dataset is build as a independent test dataset that enables fair comparison of performances of ASR systems trained with difference data.

From randomly selected 10,000 segments of videos in YouTube "TEDx talks in Japanese" playlist with manual subtitles, we manually checked and modified subtitles and timestamps of it.
In this repository, we release the scripts for reconstructing dataset as well as the list of video URLs to download so that people can reconstrct exactly the same data.

## Prerequisite
- sox
- Python 3.6+
- jaconv>=0.2.4

## Downloading audio and subtitle files
The list of URLs to be downloaded are shown in `data/tedx-jp_urls.txt`.
You can download an audio file (<video-id>.wav) and the corresponding subtitle file (<video-id>.ja.vtt) using [youtube-dl](https://github.com/ytdl-org/youtube-dl).
The following is an example script to download necessary files from YouTube to `temp/raw` directory.
```
while read youtubeurl
do
    echo ${youtubeurl}
    youtube-dl \
	--extract-audio \
	--audio-format wav \
	--write-sub \
	--sub-format vtt \
	--sub-lang ja \
	--output "temp/raw/%(id)s.%(ext)s" \
	"${youtubeurl}"
    sleep 10
done < data/tedx-jp_urls.txt
```
This requires approximately 44GB of disk space.

## Reconstructing the dataset

### The latest version dataset (recommended)
To create the latest version (1.1 as of 2021/1/13) of TEDxJP-10K, execute the following command: 
```python3 compose_tedxjp10k.py tmp/raw```

By default, resultant TEDxJP-10K corpus will be created in `TEDxJP-10K_v1.1` folder.
If you want to store the data to different place, please add `--dst_dir` option.

Please note that all the wav files will be convereted to 16kHz sampling and copied to the destination directory. So approximately 7.4GB of disk space is need.

### Old versions
To create the old version dataset (for the purpose of reproducing the experiments of our paper), `--version 1.0` command line option should be added:
```python3 compose_tedxjp10k.py --version 1.0 tmp/raw```
TEDxJP-10K corpus will be created in `TEDxJP-10K_v1.0` folder.

## Content of TEDxJP-10K
This dataset follows Kaldi-style data structure.
This include `segments`, `spk2utt`, `text` and `utt2spk` in Kaldi format.
Instead of `wav.scp`, we created `wavlist.txt` as below:
```
-6K2nN9aWsg -6K2nN9aWsg.16k.wav
0KTVqevvEjo 0KTVqevvEjo.16k.wav
```
To use in Kaldi/ESPnet, you may want to convert `wavlist.txt` file to `wav.scp` file something like this:
```
-6K2nN9aWsg sox "/path/to/TEDxJP-10K/wav/-6K2nN9aWsg.16k.wav" -c 1 -r 16000 -t wav - |
0KTVqevvEjo sox "/path/to/TEDxJP-10K/wav/0KTVqevvEjo.16k.wav" -c 1 -r 16000 -t wav - |
```
This is automatically done in the Kaldi/ESPnet recipes introduced in the next section.

All the 16kHz-sampled wav files are stored in `wav` directory.
As no full path information is included in the data, you can copy/move the dataset directory to any place you like.

## Using TEDxJP-10K

### Kaldi with LaboroTVSpeech Corpus
Please refer to the [LaboroTVSpeech](https://github.com/laboroai/LaboroTVSpeech) repository for training kaldi model using LaboroTVSpeech corpus and evaluation it with TEDxJP-10K.

### ESPnet with LaboroTVSpeech Corpus
Please refer to [the recipe included in the official ESPnet repository](https://github.com/espnet/espnet/tree/master/egs2/laborotv/) for training ESPnet model using LaboroTVSpeech corpus and evaluation it with TEDxJP-10K.


## Disclaimer
- Although we modified the transcriptions and timestamps manually, there may still be some mistakes in the data.
- Due to the update of the subtitles of the original YouTube videos, there may be a case when reconstruction of the data doesn't work properly and results in data fewer then 10k utterances.

If you encounter such situation, please inform us in issues.

## Changelog
### Version 1.1
We removed some utterances spoken in English in Aj-DXM5Zqms, Ba5Jl1_JKZY and gffgHgnEhtA.
Please refer to [this issue](https://github.com/laboroai/LaboroTVSpeech/issues/4) for detail. We appreciate eiichiroi for pointing out his error.
We also deleted some duplicated utterances in kgkvBuXAUTI video.

To compensate deleted utterances above, we added randomly selected 77 new utterances.

### Version 1.0
Initial release. This version is used in the experiments of our SLP paper.

## Citations
```
@inproceedings{ando2020slp,
  author    = {安藤慎太郎 and 藤原弘将},
  title     = {テレビ録画とその字幕を利用した大規模日本語音声コーパスの構築}
  booktitle = {情報処理学会研究報告}
  series    = {Vol.2020-SLP-134 No.8}
  date      = {2020}
}
```

## Licence
The content of this repository is released under Apache License v2.
