# !/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Make a kaldi-format data directory from pairs of .wav and .vtt files in an input directory
"""

import sys
import re
import glob
import argparse
import os
import codecs
import shutil
from pathlib import Path
import hashlib
import tempfile
import jaconv
import json
import subprocess

from logging import basicConfig, getLogger

logger = getLogger(__name__)

def convert_timestamp_to_seconds(timestamp):
    """Convert timestamp (hh:mm:ss) to seconds

    Args:
        timestamp (str): timestamp text in `hh:mm:ss` format

    Returns:
        float: timestamp converted to seconds
    """
    timestamp_split = timestamp.split(":")
    hour = int(timestamp_split[0])
    minute = int(timestamp_split[1])
    second = float(timestamp_split[2])

    second_sum = hour * 3600 + minute * 60 + second
    return second_sum


def clean_text(text):
    """Clean up one line of text in subtitles

    Args:
        text (str): input text

    Returns:
        str: output text
    """
    # Remove \U+200B
    text = text.replace("\u200b", "")

    # Han-kaku => Zen-kaku
    text = jaconv.h2z(text, kana=False, ascii=True, digit=True)

    # Remove first line
    text = re.sub(r"翻訳：.*", "", text)
    text = re.sub(r"字幕：.*", "", text)

    # Remove words in foreign languages
    text = re.sub(r"（.*語）.*", "", text)

    # Remove words added only in subtitles
    text = re.sub(r"（.*?）", "", text)  # （笑） etc.
    text = re.sub(r"［.*?］", "", text)  # [の], [を] etc.

    # Remove brackets
    text = re.sub(r"「|」|『|』|［|］|\"|“|”|＂", " ", text)

    # Remove/fix punctuation marks & Special symbols
    text = re.sub(r"！|？|、|。|…|—|・・・|．．．", " ", text)
    text = re.sub(r"〜", "ー", text)
    text = re.sub(r"♪", "", text)  # Music
    text = re.sub(r"―$", "", text)  # Music

    # Fix trailing white spaces
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+$|^\s+", "", text)

    return text


def load_vtt(vtt_path):
    """Load a vtt-format subtitle file

    Args:
        vtt_path (str): path to a .vtt file
    """
    records = []
    with codecs.open(vtt_path, "r", encoding="utf8") as f:
        read_line = False
        current_text = []
        for line in f:
            line = line.rstrip()

            # Time
            if "-->" in line:
                start_time, _, end_time = line.split()[:3]
                read_line = True

            # End of segments
            elif re.match(r"^\s*$", line):
                if current_text:
                    entry = [start_time, end_time, " ".join(current_text)]
                    records.append(entry)
                    current_text = []
                read_line = False

            # Text
            elif read_line:
                current_text.append(line)
    records = [[convert_timestamp_to_seconds(start_time), convert_timestamp_to_seconds(end_time), clean_text(text_original)]
               for start_time, end_time, text_original in records]
    return records

def main():
    """Main function"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "src_data_dir", type=Path, help="Path to directory containing .wav & .vtt files"
    )
    parser.add_argument("--dst_dir", type=Path, default=None)
    parser.add_argument("--diff_data_dir", type=Path, default=None)
    parser.add_argument("--version", type=str, default='1.1', choices=['1.1', '1.0'])
    args = parser.parse_args()

    if args.dst_dir is None:
        args.dst_dir = Path("./TEDxJP-10K_v{}".format(args.version))
    if args.diff_data_dir is None:
        args.diff_data_dir = Path("./data/{}".format(args.version))
    
    basicConfig(
        format="%(asctime)s (%(module)s:%(lineno)d) %(levelname)s: %(message)s",
        level='DEBUG',
    )

    args.dst_dir.mkdir(exist_ok=True, parents=True)

    # Files to write
    wav_scp = (args.dst_dir / "wavlist.txt").open("w")
    segments = (args.dst_dir / "segments").open("w")
    text = (args.dst_dir / "text").open("w", encoding='utf')
    utt2spk = (args.dst_dir / "utt2spk").open("w")

    uttdic={}
    for subtitle_path in sorted(glob.glob(str(args.src_data_dir / "*.ja.vtt"))):
        video_id = Path(subtitle_path).name.split(".")[0]
        wav_path = Path(subtitle_path).parent / f"{video_id}.wav"
        if not wav_path.exists():
            logger.warning(f"{wav_path} does not exist. Ignored.")
            continue
        
        records = load_vtt(subtitle_path)
        for start_sec, end_sec, subtext in records:
            if subtext == "": continue
            subtext = ''.join(subtext.split()) # Remove spaces   
            utthash = hashlib.md5((video_id+"+"+subtext).encode()).hexdigest()
            uttdic[utthash] = (video_id, subtext)

    spk2utt_dic={}
    with open(os.path.join(args.diff_data_dir, "utt_id_table.csv")) as in_file:
        for line in in_file:
            md5hash, uttid = line.strip().split()
            if md5hash not in uttdic:
                logger.warning(f"{uttid} not exist in downloaded subtitles. Ignored.")
                continue
                
            video_id, rawtext=uttdic[md5hash]

            difffile = os.path.join(args.diff_data_dir,"diffs","{}.diff".format(uttid))
            if os.path.exists(difffile):
                with open(difffile) as f:
                    diff = json.load(f)
                modtext = apply_patch(rawtext, diff)
            else:
                modtext = rawtext

            start_t = int(uttid[12:20])/100
            end_t = int(uttid[22:30])/100
                
            print(uttid, modtext, file=text)
            print(uttid, video_id, file=utt2spk)
            print(uttid, video_id, "{:.2f}".format(start_t), "{:.2f}".format(end_t), file=segments)

            if video_id not in spk2utt_dic: spk2utt_dic[video_id] = []
            spk2utt_dic[video_id].append(uttid)

    copied_wav_dir = args.dst_dir / "wav"
    copied_wav_dir.mkdir(exist_ok=True, parents=True)
    spk2utt = (args.dst_dir / "spk2utt").open("w")
    for video_id,uttids in sorted(spk2utt_dic.items()):
        print(video_id, " ".join(uttids), file=spk2utt)
        subprocess.run(['sox', Path(subtitle_path).parent / f"{video_id}.wav",
                        "-c", "1", "-r", "16000", "-t", "wav", copied_wav_dir/f"{video_id}.16k.wav"])
        print(video_id, video_id+".16k.wav", file=wav_scp)
            
def apply_patch(oldtext, patch):
    """Apply patch to subtitles

    Args:
        oldtext (str): subtitle line extracted from vtt files
        patch (list[str]): patch information
    """
    cursor=0
    newtext=[]
    for d in patch:
        if d == '':
            if len(oldtext) <= cursor:
                print("ng")
                exit(1)
            newtext.append(oldtext[cursor])
            cursor += 1
        elif d[0] == '+':
            newtext.append(d[2])
        elif d[0] == '-':
            cursor += 1
    return ''.join(newtext)


                 
if __name__ == "__main__":
    main()
