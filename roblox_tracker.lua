-- UNITED HUB - Sistema de Monitoramento Completo
-- Este código será executado no Roblox e enviará dados para o servidor

local HttpService = game:GetService("HttpService")
local Players = game:GetService("Players")
local UserInputService = game:GetService("UserInputService")
local GuiService = game:GetService("GuiService")

local player = Players.LocalPlayer

-- URL do servidor (coloque sua URL do Replit aqui)
local SERVER_URL = "https://workspace-3000--sjjssuiccisjwjw.replit.app/api/roblox-execution"

-- Função para coletar informações detalhadas do jogador
local function collectPlayerData()
    local data = {}
    
    -- Informações básicas do jogador
    data.player_name = player.Name
    data.player_display_name = player.DisplayName or player.Name
    data.player_id = player.UserId
    data.account_age = player.AccountAge
    data.membership_type = tostring(player.MembershipType)
    
    -- Informações do jogo
    data.game_id = game.GameId
    data.place_id = game.PlaceId
    data.game_name = game:GetService("MarketplaceService"):GetProductInfo(game.PlaceId).Name or "Desconhecido"
    data.server_id = game.JobId
    data.server_region = game:GetService("LocalizationService").RobloxLocaleId
    
    -- Informações técnicas
    data.platform = UserInputService:GetPlatform().Name or "Desconhecido"
    data.is_mobile = UserInputService.TouchEnabled
    data.is_gamepad = UserInputService.GamepadEnabled
    data.is_keyboard = UserInputService.KeyboardEnabled
    data.is_vr = UserInputService.VREnabled
    
    -- Informações de hardware (se disponível)
    data.graphics_quality = settings().Rendering.QualityLevel
    data.memory_usage = game:GetService("Stats"):GetTotalMemoryUsageMb()
    
    -- Timestamp
    data.timestamp = os.time()
    data.formatted_time = os.date("%d/%m/%Y %H:%M:%S")
    
    return data
end

-- Função para enviar dados para o servidor
local function sendDataToServer()
    local success, result = pcall(function()
        local playerData = collectPlayerData()
        
        local requestData = {
            Url = SERVER_URL,
            Method = "POST",
            Headers = {
                ["Content-Type"] = "application/json",
                ["User-Agent"] = "RobloxScript/UNITED-HUB"
            },
            Body = HttpService:JSONEncode(playerData)
        }
        
        return HttpService:RequestAsync(requestData)
    end)
    
    if success and result.Success then
        print("✅ UNITED HUB: Dados enviados com sucesso!")
    else
        warn("❌ UNITED HUB: Falha ao enviar dados - " .. tostring(result))
    end
end

-- Criar uma notificação visual para o jogador
local function createNotification()
    local screenGui = Instance.new("ScreenGui")
    screenGui.Name = "UnitedHubNotification"
    screenGui.ResetOnSpawn = false
    screenGui.Parent = player:WaitForChild("PlayerGui")
    
    local frame = Instance.new("Frame")
    frame.Size = UDim2.new(0, 300, 0, 80)
    frame.Position = UDim2.new(1, -320, 0, 20)
    frame.BackgroundColor3 = Color3.fromRGB(26, 26, 46)
    frame.BorderSizePixel = 0
    frame.Parent = screenGui
    
    local corner = Instance.new("UICorner")
    corner.CornerRadius = UDim.new(0, 10)
    corner.Parent = frame
    
    local title = Instance.new("TextLabel")
    title.Size = UDim2.new(1, 0, 0.5, 0)
    title.Position = UDim2.new(0, 0, 0, 0)
    title.BackgroundTransparency = 1
    title.Text = "🔑 UNITED HUB"
    title.TextColor3 = Color3.fromRGB(0, 255, 136)
    title.TextScaled = true
    title.Font = Enum.Font.GothamBold
    title.Parent = frame
    
    local message = Instance.new("TextLabel")
    message.Size = UDim2.new(1, 0, 0.5, 0)
    message.Position = UDim2.new(0, 0, 0.5, 0)
    message.BackgroundTransparency = 1
    message.Text = "Script executado com sucesso!"
    message.TextColor3 = Color3.fromRGB(255, 255, 255)
    message.TextScaled = true
    message.Font = Enum.Font.Gotham
    message.Parent = frame
    
    -- Animação de entrada
    frame:TweenPosition(
        UDim2.new(1, -320, 0, 20),
        "Out",
        "Quad",
        0.5,
        true
    )
    
    -- Remover após 5 segundos
    game:GetService("Debris"):AddItem(screenGui, 5)
    
    -- Animação de saída após 4 segundos
    wait(4)
    frame:TweenPosition(
        UDim2.new(1, 50, 0, 20),
        "In",
        "Quad",
        0.5,
        true
    )
end

-- Executar as funções
print("🔑 UNITED HUB - Iniciando monitoramento...")
print("👤 Jogador: " .. player.Name .. " (" .. player.UserId .. ")")
print("🎮 Jogo: " .. game.PlaceId)

-- Enviar dados para o servidor
sendDataToServer()

-- Mostrar notificação para o jogador
createNotification()

print("✅ UNITED HUB - Execução concluída!")