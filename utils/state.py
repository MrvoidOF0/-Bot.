# Estado compartilhado entre cogs — evita imports circulares

# {user_id: channel_id} — tickets ativos
active_tickets: dict[int, int] = {}

# {channel_id} — tickets com IA desativada
ai_disabled_tickets: set[int] = set()

# {user_id: channel_id} — canais de suporte ativos
active_support_channels: dict[int, int] = {}
