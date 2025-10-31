from config.state_license_configs import STATE_CONFIGS, get_state_config

def test_all_50_states_configured():
    """Test all 50 US states + DC have configurations"""
    assert len(STATE_CONFIGS) == 51  # 50 states + DC

def test_california_is_bulk_tier():
    """Test California configured as BULK tier"""
    ca_config = STATE_CONFIGS["CA"]
    assert ca_config["tier"] == "BULK"
    assert "download_url" in ca_config
    assert "C-10" in ca_config["license_types"]["Electrical"]

def test_massachusetts_is_api_tier():
    """Test Massachusetts configured as API tier"""
    ma_config = STATE_CONFIGS["MA"]
    assert ma_config["tier"] == "API"
    assert "api_url" in ma_config

def test_get_state_config_returns_config():
    """Test helper function returns state config"""
    config = get_state_config("TX")
    assert config is not None
    assert config["tier"] in ["BULK", "API", "SCRAPER"]

def test_get_state_config_raises_for_invalid_state():
    """Test helper raises KeyError for invalid state"""
    import pytest
    with pytest.raises(KeyError):
        get_state_config("XX")
