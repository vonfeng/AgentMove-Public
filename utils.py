"""Utility functions for AgentMove.

This module provides various utility functions for:
- Distance calculations
- File operations
- Data encoding
- JSON parsing
- Token counting
"""

from __future__ import annotations

import glob
import hashlib
import json
import os
import re
from datetime import datetime
from functools import lru_cache
from math import atan2, cos, radians, sin, sqrt
from typing import Any

import jsmin
import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder

from config import EXP_CITIES, PROCESSED_DIR
from token_count import TokenCount


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points on Earth.
    
    Args:
        lat1: Latitude of point 1 in degrees.
        lon1: Longitude of point 1 in degrees.
        lat2: Latitude of point 2 in degrees.
        lon2: Longitude of point 2 in degrees.
        
    Returns:
        Distance in kilometers.
    """
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    radius = 6371.0  # Earth's radius in kilometers
    distance = radius * c
    return distance


def create_dir(dir_path: str) -> None:
    """Create directory if it does not exist.
    
    Args:
        dir_path: Path to the directory to create.
    """
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)


def convert_time(dataset: str, model: str, original_time_str: str) -> str:
    """Convert time string to model-specific format.
    
    Args:
        dataset: Dataset name (e.g., 'Shanghai').
        model: Model name ('GETNext', 'SNPM', or 'STHM').
        original_time_str: Original time string to convert.
        
    Returns:
        Formatted time string.
        
    Raises:
        ValueError: If model is not supported.
    """
    if dataset in ['Shanghai']:  # for WWW 2019 Shanghai-ISP
        parsed_time = datetime.strptime(original_time_str, "%a %b %d %H:%M:%S %Y")
    else:
        parsed_time = datetime.strptime(original_time_str, "%a %b %d %H:%M:%S %z %Y")
    
    if model == "GETNext":
        formatted_time_str = parsed_time.strftime("%Y-%m-%d %H:%M:%S")
    elif model == "SNPM":
        formatted_time_str = parsed_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    elif model == "STHM":
        formatted_time_str = parsed_time.strftime("%Y-%m-%dT%H:%M:%S")
    else:
        raise ValueError("Unsupported model type. Supported models are: GETNext, SNPM, STHM.")
    return formatted_time_str


def string_to_md5_hex(s: str) -> str:
    """Convert string to MD5 hexadecimal hash.
    
    Args:
        s: Input string to hash.
        
    Returns:
        MD5 hash as hexadecimal string.
    """
    hash_object = hashlib.md5()
    hash_object.update(s.encode('utf-8'))
    hex_dig = hash_object.hexdigest()
    return hex_dig


def convert_timestamp(dataset: str, time_str: str) -> float:
    """Convert timestamp to fraction of day.
    
    Args:
        dataset: Dataset name.
        time_str: Time string to convert.
        
    Returns:
        Fraction of day (0.0 to 1.0).
    """
    if dataset in ['Shanghai']:  # for WWW 2019 Shanghai-ISP
        timestamp = datetime.strptime(time_str, "%a %b %d %H:%M:%S %Y")
    else:
        timestamp = datetime.strptime(time_str, "%a %b %d %H:%M:%S %z %Y")
    midnight = timestamp.replace(hour=0, minute=0, second=0)
    total_minutes = (timestamp - midnight).total_seconds() / 60
    total_minutes_in_day = 24 * 60

    fraction = total_minutes / total_minutes_in_day
    return fraction


def replace_original_poi_id(fs: pd.DataFrame) -> pd.DataFrame:
    """Replace original POI IDs with sequential integers.
    
    Args:
        fs: DataFrame containing POI data.
        
    Returns:
        DataFrame with updated PoiId column.
    """
    fs['temp_id'] = fs.groupby(['Latitude', 'Longitude', 'PoiCategoryId']).ngroup() + 1
    fs['PoiId'] = fs['temp_id']
    fs.drop(columns='temp_id', inplace=True)
    return fs


def id_encode(
    fit_df: pd.DataFrame,
    encode_df: pd.DataFrame,
    column: str,
    padding: int = -1
) -> tuple[LabelEncoder, int]:
    """Encode column values using LabelEncoder.
    
    Args:
        fit_df: DataFrame to fit the encoder on.
        encode_df: DataFrame to encode.
        column: Column name to encode.
        padding: Padding value for unknown values.
        
    Returns:
        Tuple of (LabelEncoder instance, padding_id).
    """
    id_le = LabelEncoder()
    id_le = id_le.fit(fit_df[column].values.tolist())
    if padding == 0:
        padding_id = padding
        encode_df[column] = [
            id_le.transform([i])[0] + 1 if i in id_le.classes_ else padding_id
            for i in encode_df[column].values.tolist()
        ]
    else:
        padding_id = len(id_le.classes_)
        encode_df[column] = [
            id_le.transform([i])[0] if i in id_le.classes_ else padding_id
            for i in encode_df[column].values.tolist()
        ]
    return id_le, padding_id


def ignore_first(df: pd.DataFrame) -> pd.DataFrame:
    """Ignore the first check-in sample of every trajectory.
    
    This is because there's no historical check-in for the first point.
    
    Args:
        df: DataFrame containing trajectory data.
        
    Returns:
        DataFrame with first check-ins marked as 'ignore'.
    """
    df['pseudo_session_trajectory_rank'] = df.groupby(
        'pseudo_session_trajectory_id')['UTCTimeOffset'].rank(method='first')
    df['query_pseudo_session_trajectory_id'] = df['pseudo_session_trajectory_id'].shift()
    df.loc[df['pseudo_session_trajectory_rank'] == 1, 'query_pseudo_session_trajectory_id'] = None
    df['last_checkin_epoch_time'] = df['UTCTimeOffsetEpoch'].shift()
    df.loc[df['pseudo_session_trajectory_rank'] == 1, 'last_checkin_epoch_time'] = None
    df.loc[df['UserRank'] == 1, 'SplitTag'] = 'ignore'
    df.loc[df['pseudo_session_trajectory_rank'] == 1, 'SplitTag'] = 'ignore'
    return df


def encode_poi_catid(
    fit_df: pd.DataFrame,
    encode_df: pd.DataFrame,
    source_column: str,
    target_column: str,
    padding: int = -1
) -> tuple[LabelEncoder, int]:
    """Encode POI category IDs from source column to target column.
    
    Args:
        fit_df: DataFrame to fit the encoder on.
        encode_df: DataFrame to encode.
        source_column: Source column name.
        target_column: Target column name for encoded values.
        padding: Padding value for unknown values.
        
    Returns:
        Tuple of (LabelEncoder instance, padding_id).
    """
    id_le = LabelEncoder()
    id_le = id_le.fit(fit_df[source_column].values.tolist())

    if padding == 0:
        padding_id = padding
        encode_df[target_column] = [
            id_le.transform([i])[0] + 1 if i in id_le.classes_ else padding_id
            for i in encode_df[source_column].values.tolist()
        ]
    else:
        padding_id = len(id_le.classes_)
        encode_df[target_column] = [
            id_le.transform([i])[0] if i in id_le.classes_ else padding_id
            for i in encode_df[source_column].values.tolist()
        ]

    return id_le, padding_id


@lru_cache(maxsize=128)
def int_to_days(int_day: int) -> str:
    """Convert integer day to day name string.
    
    Args:
        int_day: Integer day of week (0=Monday, 6=Sunday).
        
    Returns:
        Day name string or 'NA' if invalid.
    """
    days_of_week = {
        0: 'Monday',
        1: 'Tuesday',
        2: 'Wednesday',
        3: 'Thursday',
        4: 'Friday',
        5: 'Saturday',
        6: 'Sunday'
    }
    return days_of_week.get(int_day, "NA")


def list_predicted_users(folder_path: str) -> list[str]:
    """Get list of user IDs from prediction result files.
    
    Args:
        folder_path: Path to folder containing JSON result files.
        
    Returns:
        List of unique user IDs.
    """
    files = os.listdir(folder_path)
    files = [f for f in files if f.endswith('.json')]
    users = [f.split('_')[-2] for f in files]
    users = list(set(users))
    return users


def match_prediction(text: str, prediction_key: str = "prediction") -> list[str]:
    """Extract place IDs from prediction text using regex.
    
    Args:
        text: Text containing prediction.
        prediction_key: Key to search for ('prediction' or 'recommendation').
        
    Returns:
        List of extracted place IDs.
    """
    if prediction_key == "prediction":
        match = re.search(r'[Pp]rediction(.*?)[Rr]eason', text, re.DOTALL)
    elif prediction_key == "recommendation":
        match = re.search(r'[Rr]ecommendation(.*?)[Rr]eason', text, re.DOTALL)
    else:
        match = re.search(r'[Pp]rediction(.*?)[Rr]eason', text, re.DOTALL)
    
    if match:
        prediction_text = match.group(1)
        place_ids = re.findall(r'\b[0-9a-f]{24}\b', prediction_text)
    else:
        place_ids = []
    return place_ids


def token_count(text: str) -> int:
    """Count tokens in text using GPT tokenizer.
    
    Args:
        text: Text to count tokens for.
        
    Returns:
        Number of tokens.
    """
    tc = TokenCount(model_name="gpt-3.5-turbo")
    return tc.num_tokens_from_string(text)


def extract_json(
    full_text: str | None,
    prediction_key: str = "prediction"
) -> tuple[dict[str, Any], Any, str]:
    """Extract JSON data from LLM response text.
    
    Args:
        full_text: Full text response from LLM.
        prediction_key: Key for prediction value.
        
    Returns:
        Tuple of (output_json dict, prediction value, reason string).
    """
    if not isinstance(full_text, str):
        output_json: dict[str, Any] = {"raw_response": ""}
        prediction: Any = ""
        reason = ""
        return output_json, prediction, reason
    
    json_str = full_text[full_text.find('{'):full_text.rfind('}') + 1]
    if len(json_str) == 0:
        json_str = full_text
    
    # Remove potential comments in json_str
    try:
        json_str = jsmin.jsmin(json_str)
    except (ValueError, TypeError):
        pass  # Keep original json_str if minification fails

    try:
        output_json = json.loads(json_str)
        prediction = output_json.get(prediction_key)
        if len(prediction) == 0:
            prediction = match_prediction(output_json, prediction_key)
        reason = output_json.get('reason')
    except json.JSONDecodeError:
        prediction = full_text[full_text.find('['):full_text.rfind(']') + 1]
        reason = ""
        if len(prediction) > 0:
            try:
                prediction = json.loads(prediction)
                prediction = [int(item) for item in prediction]
            except (json.JSONDecodeError, ValueError, TypeError):
                prediction = prediction
        else:
            prediction = match_prediction(full_text, prediction_key)
        output_json = {
            "raw_response": full_text,
            "prediction": prediction,
            "reason": ""
        }
    except Exception as e:
        reason = f"Exception:{e}"
        output_json = {
            "raw_response": full_text,
            "prediction": prediction,
            "reason": reason
        }

    return output_json, prediction, reason


def token_analysis(file_path: str, include: str | None = None) -> None:
    """Analyze token counts in result files.
    
    Args:
        file_path: Glob pattern for result files.
        include: Optional filter string for file names.
    """
    print(file_path)
    file_path = os.path.join(glob.glob(file_path)[0], "*")
    print(file_path)
    if include is None:
        file_path = os.path.join(glob.glob(file_path)[0], "*")
    else:
        for file in glob.glob(file_path):
            if include in file:
                file_path = os.path.join(file, "*")
                break
    print(file_path)
    lens = []
    for file in glob.glob(file_path):
        with open(file) as fid:
            data = json.load(fid)
            input_text_len = token_count(data["input"])
            lens.append(input_text_len)
    res = (file_path, len(lens), np.percentile(lens, 0.5), np.percentile(lens, 0.9), max(lens), np.sum(lens))
    print(res)


def generate_graphs() -> None:
    """Generate social world graphs for all experiment cities."""
    from models.world_model import SocialWorld
    from processing.data import Dataset
    
    for city_name in EXP_CITIES:
        print(f"processing {city_name}")
        dataset = Dataset(
            dataset_name=city_name,
            traj_min_len=3,
            trajectory_mode="trajectory_split",
            historical_stays=16,
            context_stays=6,
            save_dir=PROCESSED_DIR,
            use_int_venue=False,
        )

        SocialWorld(
            traj_dataset=dataset,
            save_dir=PROCESSED_DIR,
            city_name=city_name,
            khop=1,
            max_neighbors=10
        )


def generate_data() -> None:
    """Generate processed data for all experiment cities."""
    from processing.data import Dataset
    
    for city_name in EXP_CITIES:
        print(f"processing {city_name}")
        Dataset(
            dataset_name=city_name,
            traj_min_len=3,
            trajectory_mode="trajectory_split",
            historical_stays=15,
            context_stays=6,
            save_dir=PROCESSED_DIR,
            use_int_venue=False,
        )


if __name__ == "__main__":
    generate_data()
