import yaml
from pathlib import Path
from typing import Dict, Any

def load_config(config_name: str) -> Dict[str, Any]:
    """설정 파일을 로드합니다."""
    config_path = Path(__file__).parent / 'config' / f'{config_name}.yaml'
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"설정 파일 로드 중 오류 발생: {str(e)}")
        return {}

if __name__ == "__main__":
    # 테스트 코드
    print(load_config('apartments'), load_config('headers'), load_config('cookies')) 
