local json = require "util.json"
local st = require "util.stanza"
local jid_bare = require "util.jid".bare

local recordings_path = os.getenv("JIBRI_RECORDINGS_PATH") or
                       module:get_option_string("jibri_recordings_path", "/recordings")

-- room_jid -> { session_id, participants = {jid -> info} }
local active_recordings = {}
-- room_jid -> { participants = {jid -> info}, created_at }
local room_states = {}

local function get_timestamp()
    return os.time()
end

local function write_event(session_id, event)
    if not session_id then
        module:log("warn", "No session_id for event: %s", event.type)
        return
    end

    local session_dir = string.format("%s/%s", recordings_path, session_id)
    local event_file = string.format("%s/events.jsonl", session_dir)

    module:log("info", "Writing event %s to %s", event.type, event_file)

    -- Create directory
    local mkdir_cmd = string.format("mkdir -p '%s' 2>&1", session_dir)
    local mkdir_result = os.execute(mkdir_cmd)
    module:log("debug", "mkdir result: %s", tostring(mkdir_result))

    local file, err = io.open(event_file, "a")
    if file then
        local json_str = json.encode(event)
        file:write(json_str .. "\n")
        file:close()
        module:log("info", "Successfully wrote event %s", event.type)
    else
        module:log("error", "Failed to write event to %s: %s", event_file, err)
    end
end

local function extract_participant_info(occupant)
    local info = {
        jid = occupant.jid,
        bare_jid = occupant.bare_jid,
        nick = occupant.nick,
        display_name = nil,
        role = occupant.role
    }

    local presence = occupant:get_presence()
    if presence then
        local nick_element = presence:get_child("nick", "http://jabber.org/protocol/nick")
        if nick_element then
            info.display_name = nick_element:get_text()
        end

        local identity = presence:get_child("identity")
        if identity then
            local user = identity:get_child("user")
            if user then
                local name = user:get_child("name")
                if name then
                    info.display_name = name:get_text()
                end

                local id_element = user:get_child("id")
                if id_element then
                    info.id = id_element:get_text()
                end
            end
        end

        if not info.display_name and occupant.nick then
            local _, _, resource = occupant.nick:match("([^@]+)@([^/]+)/(.+)")
            if resource then
                info.display_name = resource
            end
        end
    end

    return info
end

local function get_room_participant_count(room)
    local count = 0
    for _ in room:each_occupant() do
        count = count + 1
    end
    return count
end

local function snapshot_room_participants(room)
    local participants = {}
    local total = 0
    local skipped = 0

    module:log("info", "Snapshotting room participants")

    for _, occupant in room:each_occupant() do
        total = total + 1
        -- Skip recorders (Jibri)
        if occupant.bare_jid and (occupant.bare_jid:match("^recorder@") or
                                  occupant.bare_jid:match("^jibri@")) then
            skipped = skipped + 1
        else
            local info = extract_participant_info(occupant)
            participants[occupant.jid] = info
            module:log("debug", "Added participant: %s", info.display_name or info.bare_jid)
        end
    end

    module:log("info", "Snapshot: %d total, %d participants", total, total - skipped)
    return participants
end

-- Import utility functions if available
local util = module:require "util";
local get_room_from_jid = util.get_room_from_jid;
local room_jid_match_rewrite = util.room_jid_match_rewrite;

-- Main IQ handler for Jibri stanzas
module:hook("pre-iq/full", function(event)
    local stanza = event.stanza
    if stanza.name ~= "iq" then
        return
    end

    local jibri = stanza:get_child('jibri', 'http://jitsi.org/protocol/jibri')
    if not jibri then
        return
    end

    module:log("info", "=== Jibri IQ intercepted ===")

    local action = jibri.attr.action
    local session_id = jibri.attr.session_id
    local room_jid = jibri.attr.room
    local recording_mode = jibri.attr.recording_mode
    local app_data = jibri.attr.app_data

    module:log("info", "Jibri %s - session: %s, room: %s, mode: %s",
               action or "?", session_id or "?", room_jid or "?", recording_mode or "?")

    if not room_jid or not session_id then
        module:log("warn", "Missing room_jid or session_id")
        return
    end

    -- Get the room using util function
    local room = get_room_from_jid(room_jid_match_rewrite(jid_bare(stanza.attr.to)))
    if not room then
        -- Try with the room_jid directly
        room = get_room_from_jid(room_jid)
    end

    if not room then
        module:log("error", "Room not found for jid: %s", room_jid)
        return
    end

    module:log("info", "Room found: %s", room:get_name() or room_jid)

    if action == "start" then
        module:log("info", "Recording START for session %s", session_id)

        -- Count and snapshot participants
        local participant_count = 0
        for _ in room:each_occupant() do
            participant_count = participant_count + 1
        end

        local participants = snapshot_room_participants(room)
        local participant_list = {}
        for jid, info in pairs(participants) do
            table.insert(participant_list, info)
        end

        active_recordings[room_jid] = {
            session_id = session_id,
            participants = participants,
            started_at = get_timestamp()
        }

        write_event(session_id, {
            type = "recording_started",
            timestamp = get_timestamp(),
            room_jid = room_jid,
            room_name = room:get_name(),
            session_id = session_id,
            recording_mode = recording_mode,
            app_data = app_data,
            participant_count = participant_count,
            participants_at_start = participant_list
        })

    elseif action == "stop" then
        module:log("info", "Recording STOP for session %s", session_id)

        local recording = active_recordings[room_jid]
        if recording and recording.session_id == session_id then
            write_event(session_id, {
                type = "recording_stopped",
                timestamp = get_timestamp(),
                room_jid = room_jid,
                room_name = room:get_name(),
                session_id = session_id,
                duration = get_timestamp() - recording.started_at,
                participant_count = get_room_participant_count(room)
            })

            active_recordings[room_jid] = nil
        else
            module:log("warn", "No active recording found for room %s", room_jid)
        end
    end
end);

-- Room and participant event hooks
local function setup_room_hooks(host_module)
    module:log("info", "Setting up room hooks on %s", host_module.host or "unknown")

    -- Room created
    host_module:hook("muc-room-created", function(event)
        local room = event.room
        local room_jid = room.jid

        room_states[room_jid] = {
            participants = {},
            created_at = get_timestamp()
        }

        module:log("info", "Room created: %s", room_jid)
    end)

    -- Room destroyed
    host_module:hook("muc-room-destroyed", function(event)
        local room = event.room
        local room_jid = room.jid

        room_states[room_jid] = nil
        active_recordings[room_jid] = nil

        module:log("info", "Room destroyed: %s", room_jid)
    end)

    -- Occupant joined
    host_module:hook("muc-occupant-joined", function(event)
        local room = event.room
        local occupant = event.occupant
        local room_jid = room.jid

        -- Skip recorders
        if occupant.bare_jid and (occupant.bare_jid:match("^recorder@") or
                                   occupant.bare_jid:match("^jibri@")) then
            return
        end

        local participant_info = extract_participant_info(occupant)

        -- Update room state
        if room_states[room_jid] then
            room_states[room_jid].participants[occupant.jid] = participant_info
        end

        -- Log to active recording if exists
        local recording = active_recordings[room_jid]
        if recording then
            recording.participants[occupant.jid] = participant_info

            write_event(recording.session_id, {
                type = "participant_joined",
                timestamp = get_timestamp(),
                room_jid = room_jid,
                room_name = room:get_name(),
                participant = participant_info,
                participant_count = get_room_participant_count(room)
            })
        end

        module:log("info", "Participant joined %s: %s (%d total)",
                   room:get_name() or room_jid,
                   participant_info.display_name or participant_info.bare_jid,
                   get_room_participant_count(room))
    end)

    -- Occupant left
    host_module:hook("muc-occupant-left", function(event)
        local room = event.room
        local occupant = event.occupant
        local room_jid = room.jid

        -- Skip recorders
        if occupant.bare_jid and (occupant.bare_jid:match("^recorder@") or
                                   occupant.bare_jid:match("^jibri@")) then
            return
        end

        local participant_info = extract_participant_info(occupant)

        -- Update room state
        if room_states[room_jid] then
            room_states[room_jid].participants[occupant.jid] = nil
        end

        -- Log to active recording if exists
        local recording = active_recordings[room_jid]
        if recording then
            if recording.participants[occupant.jid] then
                recording.participants[occupant.jid] = nil
            end

            write_event(recording.session_id, {
                type = "participant_left",
                timestamp = get_timestamp(),
                room_jid = room_jid,
                room_name = room:get_name(),
                participant = participant_info,
                participant_count = get_room_participant_count(room)
            })
        end

        module:log("info", "Participant left %s: %s (%d remaining)",
                   room:get_name() or room_jid,
                   participant_info.display_name or participant_info.bare_jid,
                   get_room_participant_count(room))
    end)
end

-- Module initialization
local current_host = module:get_host()
local host_type = module:get_host_type()

module:log("info", "Event Logger loading on %s (type: %s)", current_host, host_type or "unknown")
module:log("info", "Recording path: %s", recordings_path)

-- Setup room hooks based on host type
if host_type == "component" and current_host:match("^[^.]+%.") then
    setup_room_hooks(module)
else
    -- Try to find and hook to MUC component
    local process_host_module = util.process_host_module
    local muc_component_host = module:get_option_string("muc_component") or
                              module:get_option_string("main_muc")

    if not muc_component_host then
        local possible_hosts = {
            "muc." .. current_host,
            "conference." .. current_host,
            "rooms." .. current_host
        }

        for _, host in ipairs(possible_hosts) do
            if prosody.hosts[host] then
                muc_component_host = host
                module:log("info", "Auto-detected MUC component: %s", muc_component_host)
                break
            end
        end
    end

    if muc_component_host then
        process_host_module(muc_component_host, function(host_module, host)
            module:log("info", "Hooking to MUC events on %s", host)
            setup_room_hooks(host_module)
        end)
    else
        module:log("error", "Could not find MUC component")
    end
end