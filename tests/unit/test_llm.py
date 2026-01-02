from src.agents.llm import get_llm, llm


def test_get_llm_returns_chat_model():
    """test get_llm returns configured ChatOpenAI instance"""
    model = get_llm()

    assert model.model_name == "x-ai/grok-4.1-fast"
    assert model.openai_api_base == "https://openrouter.ai/api/v1"
    assert model.temperature == 0.7
    assert "HTTP-Referer" in model.default_headers
    assert "X-Title" in model.default_headers


def test_get_llm_custom_model():
    """test get_llm with custom model"""
    model = get_llm(model="anthropic/claude-3.5-sonnet", temperature=0.5)

    assert model.model_name == "anthropic/claude-3.5-sonnet"
    assert model.temperature == 0.5


def test_get_llm_custom_params():
    """test get_llm with additional kwargs"""
    model = get_llm(max_tokens=1000, timeout=30)

    assert model.max_tokens == 1000
    assert model.request_timeout == 30


def test_default_llm_instance():
    """test default llm instance is configured"""
    assert llm.model_name == "x-ai/grok-4.1-fast"
    assert llm.openai_api_base == "https://openrouter.ai/api/v1"


def test_llm_headers_from_settings():
    """test llm uses headers from settings"""
    model = get_llm()

    assert model.default_headers["HTTP-Referer"] == "http://localhost:3000"
    assert model.default_headers["X-Title"] == "AgreeToDisagree"


def test_llm_supports_structured_output():
    """test llm has with_structured_output method"""
    assert hasattr(llm, "with_structured_output")
    assert callable(llm.with_structured_output)


def test_llm_supports_invoke():
    """test llm has invoke and ainvoke methods"""
    assert hasattr(llm, "invoke")
    assert hasattr(llm, "ainvoke")
    assert callable(llm.invoke)
    assert callable(llm.ainvoke)
