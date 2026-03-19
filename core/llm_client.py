"""
大模型客户端 - 支持 Qwen API 和 Ollama/LM Studio
"""
import json
import logging
from typing import Optional, Callable, AsyncGenerator, List
from openai import OpenAI


class BaseLLMClient:
    """大模型客户端基类"""

    def __init__(self, api_key: str, model: str = "qwen3.5-plus", base_url: str = "https://coding.dashscope.aliyuncs.com/v1"):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        """使用 OpenAI 库同步生成回答"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=False,
            max_completion_tokens=500
        )
        return response.choices[0].message.content


    async def generate_stream(self, prompt: str, system_prompt: str = "",
                              callback: Optional[Callable[[str], None]] = None) -> str:
        """使用 OpenAI 库流式生成回答"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        stream = client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
            max_completion_tokens=500
        )
        
        full_content = ""
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_content += content
                if callback:
                    callback(content)
        
        return full_content

class LMStudioClient(BaseLLMClient):
    """LM Studio 客户端 (使用 OpenAI 库)"""

    def __init__(self, base_url: str, model: str = "local-model"):
        self.base_url = base_url.rstrip('/')
        self.model = model
        # 使用 OpenAI 库
        self.client = OpenAI(
            api_key="not-needed",  # LM Studio 不需要 API Key
            base_url=f"{self.base_url}/v1"
        )

    async def generate(self, prompt: str, system_prompt: str = "", callback=None) -> str:
        """使用 OpenAI 库同步生成回答"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500,
                stream=False
            )
            content = response.choices[0].message.content
            if content:
                return self._extract_answer_from_qwen3_content(content)
            return ""
        except Exception as e:
            if "503" in str(e):
                raise Exception("LM Studio 服务不可用 (503 错误) - 请确保 LM Studio 已启动并加载了模型")
            raise Exception(f"LM Studio 请求失败：{str(e)}")


    async def generate_stream(self, prompt: str, system_prompt: str = "",
                              callback: Optional[Callable[[str], None]] = None) -> str:
        """使用 OpenAI 库流式生成回答"""
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500,
                stream=True
            )
            
            full_content = ""
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_content += content
                    # 提取答案并回调
                    extracted = self._extract_answer_from_qwen3_content(content)
                    if callback and extracted:
                        callback(extracted)
            
            return full_content
        except Exception as e:
            if "503" in str(e):
                raise Exception("LM Studio 服务不可用 (503 错误) - 请确保 LM Studio 已启动并加载了模型")
            raise Exception(f"LM Studio 请求失败：{str(e)}")
    
    def get_available_models(self) -> List[str]:
        """获取 LM Studio 可用模型列表"""
        try:
            import requests
            response = requests.get(f"{self.base_url}/api/v1/models", timeout=5)
            if response.status_code == 200:
                data = response.json()
                # 提取 LLM 类型的模型 key
                models = [
                    model["key"] for model in data.get("models", [])
                    if model.get("type") == "llm"
                ]
                return models
            return []
        except Exception as e:
            print(f"获取模型列表失败：{e}")
            return []


        return full_content

    def _extract_answer_from_qwen3_content(self, content: str) -> str:
        """Extract just the answer part from Qwen3 model's thinking process output"""
        if not content:
            return ""
        
        # Clean up the content first
        content = content.strip()
        
        # The Qwen3 model outputs thinking process in this format:
        # \Thinking Process:\n\n1. ...\n\n2. ...\n\n...\n\n\n\n<answer>
        # We need to extract everything after the last clear thinking process separator
        
        # Look for the pattern that separates thinking from answer
        # Based on observation, it's often multiple newlines or a clear delimiter
        
        # Method 1: Split by "\n\n\n\n" (4 newlines) which seems to be the separator
        if "\n\n\n\n" in content:
            parts = content.split("\n\n\n\n")
            # The answer should be in the last part
            answer_part = parts[-1].strip()
            if answer_part:
                return answer_part
        
        # Method 2: Look for the thinking process marker and take everything after it ends
        thinking_marker = r"\Thinking Process:"
        if thinking_marker in content:
            # Find the end of the thinking process
            # Look for a pattern that indicates the thinking is done
            # Based on samples, it ends with a constructed response and then separator
            
            # Find the thinking process section
            thinking_start = content.find(thinking_marker)
            if thinking_start != -1:
                # Look for the end of thinking - look for common ending patterns
                # In the samples, it often ends with something like:
                # "6.  **Construct Response:** \"4\".\n\n\n\n\n4"
                # or similar pattern
                
                # Try to find where the actual answer starts after the thinking
                # Look for the last occurrence of a number or short answer at the end
                lines = content.split('\n')
                
                # Start from the end and look for the actual answer line
                for i in range(len(lines) - 1, -1, -1):
                    line = lines[i].strip()
                    # Skip empty lines and lines that are clearly part of thinking
                    if not line:
                        continue
                    # Skip lines that contain thinking process markers
                    if any(marker in line.lower() for marker in [
                        'analyze', 'identify', 'execute', 'formulate', 'final', 
                        'check', 'construct', 'response:', 'decision:', 'option',
                        'draft:', 'refinement:', 'choice:', 'wait:', 'let:', 
                        'keep:', 'step:', 'phase:', 'stage:', 'review', 'safety',
                        'nuance', 'context', 'policy', 'violate'
                    ]):
                        continue
                    # If we find a line that looks like an answer (short, contains result)
                    # and it's not preceded by thinking markers on the same line
                    if len(line) < 20 and any(c.isdigit() for c in line):
                        # Additional check: make sure it's not part of a thinking step
                        if not any(prefix in line for prefix in ['1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '10.']):
                            return line
                
                # Fallback: take everything after the last thinking-like line
                # Find where thinking process likely ends
                for i in range(len(lines) - 1, -1, -1):
                    line = lines[i].strip()
                    if line.endswith('".') or line.endswith("'.") or line.isdigit() or (len(line) < 10 and any(c.isdigit() for c in line)):
                        # Check if this looks like an answer line
                        if not any(marker in line.lower() for marker in [
                            'analyze', 'identify', 'execute', 'formulate', 'final', 
                            'check', 'construct', 'response:', 'decision:', 'option'
                        ]):
                            # Return this line and any following lines that look like continuation
                            answer_lines = []
                            for j in range(i, len(lines)):
                                answer_line = lines[j].strip()
                                if answer_line:
                                    # Stop if we hit another thinking marker
                                    if any(marker in answer_line.lower() for marker in [
                                        'analyze', 'identify', 'execute', 'formulate', 'final', 
                                        'check', 'construct', 'response:', 'decision:', 'option'
                                    ]) and j > i:  # Only stop if it's not the same line
                                        break
                                    answer_lines.append(answer_line)
                            return ' '.join(answer_lines).strip()
        
        # Method 3: Simple approach - take the last non-empty line that looks like an answer
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        if lines:
            # Check from the end for the answer
            for line in reversed(lines):
                # Skip obvious thinking process lines
                if any(skip in line.lower() for skip in [
                    'analyze', 'identify', 'execute', 'formulate', 'select', 'check', 
                    'final', 'option', 'draft', 'refinement', 'choice', 
                    'wait', 'let', 'keep', 'step', 'phase', 'stage',
                    'review', 'construct', 'response', 'decision', 'safety',
                    'nuance', 'context', 'policy', 'violate', 'trick'
                ]):
                    continue
                # If it's a short line that looks like an answer
                if len(line) < 50 and not line.startswith('*') and not line.startswith('-'):
                    # Clean up common answer prefixes
                    cleaned = line
                    for prefix in ['Answer:', 'The answer is:', 'Final Answer:', '答案：', '答案是：']:
                        if cleaned.startswith(prefix):
                            cleaned = cleaned[len(prefix):].strip()
                    # Remove quotes if they wrap the entire answer
                    if cleaned.startswith('"') and cleaned.endswith('"') and len(cleaned) > 2:
                        cleaned = cleaned[1:-1]
                    if cleaned.startswith("'") and cleaned.endswith("'") and len(cleaned) > 2:
                        cleaned = cleaned[1:-1]
                    if cleaned:
                        return cleaned
        
        # Fallback: return original content (shouldn't happen often)
        return content


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
