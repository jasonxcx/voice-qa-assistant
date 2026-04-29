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

    async def generate(self, prompt: str, system_prompt: str = "",
                      temperature: float = 0.3,
                      max_completion_tokens: int = 500,
                      reasoning_effort: str = "none") -> str:
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
            temperature=temperature,
            max_completion_tokens=max_completion_tokens,
            reasoning_effort=reasoning_effort
        )
        return response.choices[0].message.content


    async def generate_stream(self, prompt: str, system_prompt: str = "",
                              callback: Optional[Callable[[str], None]] = None,
                              temperature: float = 0.3,
                              max_completion_tokens: int = 1000,
                              reasoning_effort: str = "none") -> str:
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
            temperature=temperature,
            max_completion_tokens=max_completion_tokens,
            reasoning_effort=reasoning_effort
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

    def build_system_prompt(self, document_text: str = "", history_text: str = "") -> str:
        """
        构建系统提示词

        Args:
            document_text: 导入的文档文本
            history_text: 历史对话上下文（可选）

        Returns:
            系统提示词
        """
        base_prompt = self.config.llm_system_prompt_base

        if document_text:
            # 有文档时，追加文档信息
            base_prompt += f"""

## 文档信息
{document_text}

请结合以上文档信息，生成回答。"""

        # 在文档信息之后、回答规则之前插入历史上下文
        if history_text:
            base_prompt += f"""

{history_text}"""

        base_prompt += f"""
## 回答规则
1. **简短精炼**: 每个回答控制在 {self.config.llm_prompts_words} 字，只列出关键点
2. **结构化**: 用要点列表格式，每点一句话，不要用markdown标题（#、##、###）
3. **避免废话**: 不要使用"我认为"、"我觉得"等填充词
4. **直接回答**: 收到问题后直接给出要点答案，不要先解释问题是什么

## 输出格式
请直接用简体中文输出回答内容，不要有任何前缀或解释。不要输出思考过程，只输出最终答案。
"""

        return base_prompt

    async def generate_answer(self, question: str, resume_data: Optional[dict] = None, history_text: str = "") -> str:
        """
        生成回答

        Args:
            question: 问题文本
            resume_data: 文档数据（可选）
            history_text: 历史对话上下文（可选）

        Returns:
            AI 生成的回答
        """
        from core.resume_parser import ResumeParser

        document_text = ""
        if resume_data:
            parser = ResumeParser()
            document_text = parser.format_for_prompt(resume_data)

        system_prompt = self.build_system_prompt(document_text, history_text)

        # 简短回答的 Prompt 强化
        prompt = f"""请回答以下问题（{self.config.llm_prompts_words} 字，只列关键点）：

问题：{question}（来自语音转文字，可能音译的不准确，需要尽你所能匹配为{self.config.llm_prompts_theme}会问到的题）

回答："""

        return await self.client.generate(
            prompt, system_prompt,
            temperature=self.config.llm_temperature,
            max_completion_tokens=self.config.llm_max_completion_tokens,
            reasoning_effort=self.config.llm_reasoning_effort
        )

    async def generate_answer_stream(self, question: str,
                                     resume_data: Optional[dict] = None,
                                     callback: Optional[Callable[[str], None]] = None,
                                     history_text: str = "") -> str:
        """
        流式生成回答

        Args:
            question: 问题文本
            resume_data: 文档数据（可选）
            callback: 每收到一段文本的回调函数
            history_text: 历史对话上下文（可选）

        Returns:
            AI 生成的完整回答
        """
        from core.resume_parser import ResumeParser

        document_text = ""
        if resume_data:
            parser = ResumeParser()
            document_text = parser.format_for_prompt(resume_data)

        system_prompt = self.build_system_prompt(document_text, history_text)

        prompt = f"""请回答以下问题（{self.config.llm_prompts_words} 字，只列关键点）：

问题：{question}（语音转文字可能音译的不准确，需要尽你所能匹配为{self.config.llm_prompts_theme}会问到的题）

回答："""

        return await self.client.generate_stream(
            prompt, system_prompt, callback,
            temperature=self.config.llm_temperature,
            max_completion_tokens=self.config.llm_max_completion_tokens_stream,
            reasoning_effort=self.config.llm_reasoning_effort
        )

    async def generate_followup_suggestions(self, question: str, answer: str, 
                                           history_text: str = "",
                                           max_suggestions: int = 3) -> list:
        """
        生成追问建议
        
        Args:
            question: 当前问题
            answer: 当前回答
            history_text: 历史对话上下文
            max_suggestions: 最大追问建议数量
            
        Returns:
            追问建议列表
        """
        # 构建追问建议 prompt
        followup_prompt = f"""你是一个专业的面试官。基于以下对话上下文，生成 {max_suggestions} 个追问建议（用于深度挖掘候选人知识）。

{history_text if history_text else ""}

当前问题：{question}
当前回答：{answer}

请生成 {max_suggestions} 个追问建议，要求：
1. 与当前话题相关
2. 有深度，能进一步考察候选人
3. 用简洁的疑问句格式
4. 只输出追问问题，每行一个，不要编号，不要额外解释

追问建议："""

        system_prompt = f"""你是一个专业的{self.config.llm_prompts_theme}面试官。
请生成简洁、有深度的追问问题。
只输出问题本身，不要任何前缀或解释。"""

        try:
            response = await self.client.generate(
                followup_prompt, system_prompt,
                temperature=0.7,  # 稍高温度以生成多样化问题
                max_completion_tokens=300,
                reasoning_effort="none"
            )
            
            # 解析追问建议（每行一个）
            suggestions = [s.strip() for s in response.strip().split('\n') if s.strip()]
            
            # 限制数量
            suggestions = suggestions[:max_suggestions]
            
            # 添加"仅供参考"前缀
            suggestions = [f"（仅供参考）{s}" for s in suggestions]
            
            return suggestions
        except Exception as e:
            print(f"[LLM] 生成追问建议失败：{e}", flush=True)
            return []

if __name__ == '__main__':
    from core.config import get_config
    import asyncio
    llm_client = LLMClient(get_config())
    asyncio.run(llm_client.generate_answer_stream("请讲一下TCP的3次握手和四次挥手"))