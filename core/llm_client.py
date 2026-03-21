"""
大模型客户端 - 支持 Qwen API 和 Ollama/LM Studio
"""
import json
import logging
from typing import Optional, Callable
from openai import OpenAI


class BaseLLMClient:
    """大模型客户端基类"""

    def __init__(self, api_key: str, model: str = "qwen3.5-plus", base_url: str = "https://coding.dashscope.aliyuncs.com/v1"):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        print(f"[LLM] 使用 OpenAI 库同步生成回答", flush=True)
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=False,
            temperature=0.3,
            max_completion_tokens=500,
            reasoning_effort='none'
        )
        return response.choices[0].message.content


    async def generate_stream(self, prompt: str, system_prompt: str = "",
                              callback: Optional[Callable[[str], None]] = None) -> str:
        print(f"[LLM] 使用 OpenAI 库流式生成回答")
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        stream = client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
            temperature=0.3,
            max_completion_tokens=1000,
            reasoning_effort='none'
        )
        full_content = ""
        for chunk in stream:
            if chunk.choices:
                delta = chunk.choices[0].delta
                if hasattr(delta, 'content') and delta.content:
                    content = delta.content
                    full_content += content
                    if callback:
                        callback(content)
                    # 调试日志：输出完整的 chunk
                    print(delta.content, end="")
                elif hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                    print(delta.reasoning_content, end="")

        print(f"\n[LLM] 流式生成完成，总内容长度：{len(full_content)}", flush=True)
        return full_content


class LLMClient:
    """统一大模型客户端 - 根据配置自动选择后端"""

    def __init__(self, config):
        self.config = config
        self.client = self._create_client()

    def switch_mode(self):
        """切换 LLM 模式"""
        self.client = self._create_client()
    def _create_client(self) -> BaseLLMClient:
        """根据配置创建客户端 - 使用统一配置"""
        model = self.config.llm_model
        base_url = self.config.llm_base_url
        if self.config.llm_mode == "lmstudio":
            base_url += "/v1"
        api_key = self.config.llm_api_key
        return BaseLLMClient(
            api_key=api_key,
            model=model,
            base_url=base_url
        )

    def build_system_prompt(self, resume_text: str = "") -> str:
        """
        构建系统提示词

        Args:
            resume_text: 简历文本

        Returns:
            系统提示词
        """
        base_prompt = "你是一个熟悉计算机专业知识的Java工程师助手。"
        if resume_text:
            base_prompt += f"""{base_prompt}

## 面试者简历信息
{resume_text}
请基于以上简历信息，结合面试者的实际经历，为面试者生成回答。"""

        base_prompt +="""
## 回答规则
1. **简短精炼**: 每个回答控制在 100-200 字，只列出关键点
2. **结构化**: 列举要点，每点一句话
3. **避免废话**: 不要使用"我认为"、"我觉得"等填充词

## 输出格式
请直接用简体中文输出回答内容，不要有任何前缀或解释。不要输出思考过程，只输出最终答案。
"""

        return base_prompt

    async def generate_answer(self, question: str, resume_data: Optional[dict] = None) -> str:
        """
        生成面试回答

        Args:
            question: 面试问题
            resume_data: 简历数据（可选）

        Returns:
            AI 生成的回答
        """
        from core.resume_parser import ResumeParser

        resume_text = ""
        if resume_data:
            parser = ResumeParser()
            resume_text = parser.format_for_prompt(resume_data)

        system_prompt = self.build_system_prompt(resume_text)

        # 简短回答的 Prompt 强化
        prompt = f"""请回答以下面试问题（100-200 字，只列关键点）：

问题：{question}（来自于面试官的语音转文字可能音译的不准确，需要尽你所能匹配为Java技术面试会问到的题）

回答："""

        return await self.client.generate(prompt, system_prompt)

    async def generate_answer_stream(self, question: str,
                                     resume_data: Optional[dict] = None,
                                     callback: Optional[Callable[[str], None]] = None) -> str:
        """
        流式生成面试回答

        Args:
            question: 面试问题
            resume_data: 简历数据（可选）
            callback: 每收到一段文本的回调函数

        Returns:
            AI 生成的完整回答
        """
        from core.resume_parser import ResumeParser

        resume_text = ""
        if resume_data:
            parser = ResumeParser()
            resume_text = parser.format_for_prompt(resume_data)

        system_prompt = self.build_system_prompt(resume_text)

        prompt = f"""请回答以下面试问题（100-200 字，只列关键点）：

问题：{question}（来自于面试官的语音转文字可能音译的不准确，需要尽你所能匹配为Java技术面试会问到的题）

回答："""

        return await self.client.generate_stream(prompt, system_prompt, callback)
