import asyncio
import time
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx


class PluggyError(Exception):
    """Erro de integração Pluggy com status HTTP sugerido para a resposta."""

    def __init__(self, message: str, status_code: int = 502) -> None:
        """Guarda mensagem e status.

        Args:
            message: Descrição amigável do erro.
            status_code: HTTP a devolver ao chamador (padrão 502).
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class PluggyClient:
    """Cliente assíncrono da API Pluggy com API key em cache (somente memória)."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        api_url: str = "https://api.pluggy.ai",
        timeout: float = 15.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """Configura credenciais, endpoint e cliente HTTP.

        Args:
            client_id: Client ID da aplicação Pluggy.
            client_secret: Client secret (nunca persistido).
            api_url: Base da API Pluggy.
            timeout: Timeout por requisição, em segundos.
            http_client: Cliente injetado (testes); quando omitido, um é criado.
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.api_url = api_url.rstrip("/")
        self._client = http_client or httpx.AsyncClient(base_url=self.api_url, timeout=timeout)
        self._owns_client = http_client is None
        self._api_key: str | None = None
        self._api_key_expires_at = 0.0
        self._auth_lock = asyncio.Lock()

    async def close(self) -> None:
        """Fecha o cliente HTTP próprio; clientes injetados são do chamador."""
        if self._owns_client:
            await self._client.aclose()

    async def get_api_key(self, force_refresh: bool = False) -> str:
        """Obtém a API key temporária, reutilizando o cache válido por ~2h.

        Args:
            force_refresh: Ignora o cache e autentica novamente.

        Raises:
            PluggyError: Sem credenciais, timeout, resposta inesperada ou 401/403.

        Returns:
            API key válida para o cabeçalho `X-API-KEY`.
        """
        if not self.client_id or not self.client_secret:
            raise PluggyError("Credenciais da Pluggy não configuradas.", 503)
        if not force_refresh and self._api_key and time.monotonic() < self._api_key_expires_at:
            return self._api_key

        async with self._auth_lock:
            if not force_refresh and self._api_key and time.monotonic() < self._api_key_expires_at:
                return self._api_key
            try:
                response = await self._client.post(
                    "/auth",
                    json={"clientId": self.client_id, "clientSecret": self.client_secret},
                )
            except httpx.TimeoutException as exc:
                raise PluggyError("A Pluggy demorou para responder. Tente novamente.", 504) from exc
            except httpx.RequestError as exc:
                raise PluggyError("Não foi possível acessar a Pluggy.", 503) from exc
            if response.status_code in {401, 403}:
                raise PluggyError("Credenciais da Pluggy inválidas.", 503)
            if response.is_error:
                raise PluggyError("Não foi possível gerar a chave de acesso da Pluggy.")
            try:
                api_key = response.json()["apiKey"]
            except (ValueError, KeyError, TypeError) as exc:
                raise PluggyError("A Pluggy retornou uma resposta inesperada.") from exc
            if not isinstance(api_key, str) or not api_key:
                raise PluggyError("A Pluggy retornou uma resposta inesperada.")
            self._api_key = api_key
            # A chave vale 2 horas; a margem evita usá-la perto da expiração.
            self._api_key_expires_at = time.monotonic() + 115 * 60
            return api_key

    async def _request(self, method: str, path: str, *, params: dict[str, Any] | None = None, json: dict[str, Any] | None = None) -> dict[str, Any]:
        """Executa uma chamada autenticada com 1 retentativa após refresh de chave.

        Args:
            method: Verbo HTTP.
            path: Caminho relativo à base da API.
            params: Query params.
            json: Corpo JSON.

        Raises:
            PluggyError: Falha de rede, autenticação, rate limit ou payload inválido.

        Returns:
            Corpo da resposta como dicionário.
        """
        for attempt in range(2):
            key = await self.get_api_key(force_refresh=attempt == 1)
            try:
                response = await self._client.request(
                    method, path, params=params, json=json, headers={"X-API-KEY": key}
                )
            except httpx.TimeoutException as exc:
                raise PluggyError("A Pluggy demorou para responder. Tente novamente.", 504) from exc
            except httpx.RequestError as exc:
                raise PluggyError("A Pluggy está indisponível no momento.", 503) from exc
            if response.status_code in {401, 403} and attempt == 0:
                continue
            if response.status_code == 404:
                raise PluggyError("Recurso não encontrado na Pluggy.", 404)
            if response.status_code in {401, 403}:
                raise PluggyError("Não foi possível autenticar na Pluggy.", 502)
            if response.status_code == 429:
                raise PluggyError("Limite de requisições da Pluggy atingido. Tente mais tarde.", 503)
            if response.is_error:
                raise PluggyError("A Pluggy não conseguiu concluir a solicitação.", 502)
            try:
                data = response.json()
            except ValueError as exc:
                raise PluggyError("A Pluggy retornou uma resposta inesperada.") from exc
            if not isinstance(data, dict):
                raise PluggyError("A Pluggy retornou uma resposta inesperada.")
            return data
        raise PluggyError("Não foi possível autenticar na Pluggy.")

    async def create_connect_token(self) -> str:
        """Cria o token do widget Pluggy Connect para o usuário local único.

        Raises:
            PluggyError: Quando a API não devolve um token válido.

        Returns:
            Token de conexão (`connectToken`/`accessToken`).
        """
        data = await self._request(
            "POST", "/connect_token", json={"options": {"clientUserId": "local-mvp-user"}}
        )
        token = data.get("connectToken") or data.get("accessToken")
        if not isinstance(token, str) or not token:
            raise PluggyError("Não foi possível gerar o token de conexão.")
        return token

    async def get_item(self, item_id: str) -> dict[str, Any]:
        """Busca um item (conexão bancária) pelo id.

        Args:
            item_id: Identificador do item na Pluggy.

        Returns:
            Payload do item.
        """
        return await self._request("GET", f"/items/{item_id}")

    async def get_accounts(self, item_id: str) -> list[dict[str, Any]]:
        """Lista contas de um item.

        Args:
            item_id: Identificador do item na Pluggy.

        Raises:
            PluggyError: Quando `results` não é uma lista.

        Returns:
            Contas do item.
        """
        data = await self._request("GET", "/accounts", params={"itemId": item_id})
        results = data.get("results", [])
        if not isinstance(results, list):
            raise PluggyError("A Pluggy retornou uma resposta inesperada.")
        return results

    async def get_transactions(self, account_id: str, date_from: str, date_to: str, limit: int = 500) -> list[dict[str, Any]]:
        """Busca transações com paginação por cursor até o limite.

        Args:
            account_id: Conta na Pluggy.
            date_from: Início (formato da API).
            date_to: Fim (formato da API).
            limit: Máximo de transações acumuladas.

        Returns:
            Transações no período, até `limit` itens.
        """
        transactions: list[dict[str, Any]] = []
        after: str | None = None
        while len(transactions) < limit:
            params: dict[str, Any] = {
                "accountId": account_id,
                "dateFrom": date_from,
                "dateTo": date_to,
            }
            if after:
                params["after"] = after
            data = await self._request("GET", "/v2/transactions", params=params)
            results = data.get("results", [])
            if not isinstance(results, list):
                raise PluggyError("A Pluggy retornou uma resposta inesperada.")
            transactions.extend(results[: limit - len(transactions)])
            if len(transactions) >= limit:
                break
            next_value = data.get("next")
            if not isinstance(next_value, str) or not next_value:
                break
            after_values = parse_qs(urlparse(next_value).query).get("after")
            if not after_values or after_values[0] == after:
                break
            after = after_values[0]
        return transactions
