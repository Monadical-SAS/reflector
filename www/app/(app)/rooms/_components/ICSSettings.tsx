import {
  VStack,
  HStack,
  Field,
  Input,
  Select,
  Checkbox,
  Button,
  Text,
  Badge,
  createListCollection,
  Spinner,
  Box,
  IconButton,
} from "@chakra-ui/react";
import { useState, useEffect, useRef } from "react";
import { LuRefreshCw, LuCopy, LuCheck } from "react-icons/lu";
import { FaCheckCircle, FaExclamationCircle } from "react-icons/fa";
import { useRoomIcsSync, useRoomIcsStatus } from "../../../lib/apiHooks";
import { toaster } from "../../../components/ui/toaster";
import { roomAbsoluteUrl } from "../../../lib/routesClient";
import {
  assertExists,
  NonEmptyString,
  parseNonEmptyString,
} from "../../../lib/utils";

interface ICSSettingsProps {
  roomName: NonEmptyString | null;
  icsUrl?: string;
  icsEnabled?: boolean;
  icsFetchInterval?: number;
  icsLastSync?: string;
  icsLastEtag?: string;
  onChange: (settings: Partial<ICSSettingsData>) => void;
  isOwner?: boolean;
  isEditing?: boolean;
}

export interface ICSSettingsData {
  ics_url: string;
  ics_enabled: boolean;
  ics_fetch_interval: number;
}

const fetchIntervalOptions = [
  { label: "1 minute", value: "1" },
  { label: "5 minutes", value: "5" },
  { label: "10 minutes", value: "10" },
  { label: "30 minutes", value: "30" },
  { label: "1 hour", value: "60" },
];

export default function ICSSettings({
  roomName,
  icsUrl = "",
  icsEnabled = false,
  icsFetchInterval = 5,
  icsLastSync,
  icsLastEtag,
  onChange,
  isOwner = true,
  isEditing = false,
}: ICSSettingsProps) {
  const [syncStatus, setSyncStatus] = useState<
    "idle" | "syncing" | "success" | "error"
  >("idle");
  const [syncMessage, setSyncMessage] = useState<string>("");
  const [syncResult, setSyncResult] = useState<{
    eventsFound: number;
    totalEvents: number;
    eventsCreated: number;
    eventsUpdated: number;
  } | null>(null);
  const [justCopied, setJustCopied] = useState(false);
  const roomUrlInputRef = useRef<HTMLInputElement>(null);

  const syncMutation = useRoomIcsSync();

  const fetchIntervalCollection = createListCollection({
    items: fetchIntervalOptions,
  });

  const handleCopyRoomUrl = async () => {
    try {
      await navigator.clipboard.writeText(
        roomAbsoluteUrl(assertExists(roomName)),
      );
      setJustCopied(true);

      toaster
        .create({
          placement: "top",
          duration: 3000,
          render: ({ dismiss }) => (
            <Box
              bg="green.500"
              color="white"
              px={4}
              py={3}
              borderRadius="md"
              display="flex"
              alignItems="center"
              gap={2}
              boxShadow="lg"
            >
              <LuCheck />
              <Text>Room URL copied to clipboard!</Text>
            </Box>
          ),
        })
        .then(() => {});

      setTimeout(() => {
        setJustCopied(false);
      }, 2000);
    } catch (err) {
      console.error("Failed to copy room url:", err);
    }
  };

  const handleRoomUrlClick = () => {
    if (roomUrlInputRef.current) {
      roomUrlInputRef.current.select();
      handleCopyRoomUrl().then(() => {});
    }
  };

  // Clear sync results when dialog closes
  useEffect(() => {
    if (!isEditing) {
      setSyncStatus("idle");
      setSyncResult(null);
      setSyncMessage("");
    }
  }, [isEditing]);

  const handleForceSync = async () => {
    if (!roomName || !isEditing) return;

    // Clear previous results
    setSyncStatus("syncing");
    setSyncResult(null);
    setSyncMessage("");

    try {
      const result = await syncMutation.mutateAsync({
        params: {
          path: { room_name: roomName },
        },
      });

      if (result.status === "success" || result.status === "unchanged") {
        setSyncStatus("success");
        setSyncResult({
          eventsFound: result.events_found || 0,
          totalEvents: result.total_events || 0,
          eventsCreated: result.events_created || 0,
          eventsUpdated: result.events_updated || 0,
        });
      } else {
        setSyncStatus("error");
        setSyncMessage(result.error || "Sync failed");
      }
    } catch (err: any) {
      setSyncStatus("error");
      setSyncMessage(err.body?.detail || "Failed to force sync calendar");
    }
  };

  if (!isOwner) {
    return null; // ICS settings only visible to room owner
  }

  return (
    <VStack gap={4} align="stretch">
      <Field.Root>
        <Checkbox.Root
          checked={icsEnabled}
          onCheckedChange={(e) => onChange({ ics_enabled: !!e.checked })}
        >
          <Checkbox.HiddenInput />
          <Checkbox.Control>
            <Checkbox.Indicator />
          </Checkbox.Control>
          <Checkbox.Label>Enable ICS calendar sync</Checkbox.Label>
        </Checkbox.Root>
      </Field.Root>

      {icsEnabled && (
        <>
          <Field.Root>
            <Field.Label>Room URL</Field.Label>
            <Field.HelperText>
              To enable Reflector to recognize your calendar events as meetings,
              add this URL as the location in your calendar events
            </Field.HelperText>
            {roomName ? (
              <HStack gap={0} position="relative" width="100%">
                <Input
                  ref={roomUrlInputRef}
                  value={roomAbsoluteUrl(parseNonEmptyString(roomName))}
                  readOnly
                  onClick={handleRoomUrlClick}
                  cursor="pointer"
                  bg="gray.100"
                  _hover={{ bg: "gray.200" }}
                  _focus={{ bg: "gray.200" }}
                  pr="90px"
                  width="100%"
                />
                <HStack position="absolute" right="4px" gap={1} zIndex={1}>
                  <IconButton
                    aria-label="Copy room URL"
                    onClick={handleCopyRoomUrl}
                    variant="ghost"
                    size="sm"
                  >
                    {justCopied ? <LuCheck /> : <LuCopy />}
                  </IconButton>
                </HStack>
              </HStack>
            ) : null}
          </Field.Root>

          <Field.Root>
            <Field.Label>ICS Calendar URL</Field.Label>
            <Input
              placeholder="https://calendar.google.com/calendar/ical/..."
              value={icsUrl}
              onChange={(e) => onChange({ ics_url: e.target.value })}
            />
            <Field.HelperText>
              Enter the ICS URL from Google Calendar, Outlook, or other calendar
              services
            </Field.HelperText>
          </Field.Root>

          <Field.Root>
            <Field.Label>Sync Interval</Field.Label>
            <Select.Root
              collection={fetchIntervalCollection}
              value={[icsFetchInterval.toString()]}
              onValueChange={(details) => {
                const value = parseInt(details.value[0]);
                onChange({ ics_fetch_interval: value });
              }}
            >
              <Select.Trigger>
                <Select.ValueText />
              </Select.Trigger>
              <Select.Content>
                {fetchIntervalOptions.map((option) => (
                  <Select.Item key={option.value} item={option}>
                    {option.label}
                  </Select.Item>
                ))}
              </Select.Content>
            </Select.Root>
            <Field.HelperText>
              How often to check for calendar updates
            </Field.HelperText>
          </Field.Root>

          {icsUrl && isEditing && roomName && (
            <HStack gap={3}>
              <Button
                size="sm"
                variant="outline"
                onClick={handleForceSync}
                disabled={syncStatus === "syncing"}
              >
                {syncStatus === "syncing" ? (
                  <Spinner size="sm" />
                ) : (
                  <LuRefreshCw />
                )}
                Force Sync
              </Button>
            </HStack>
          )}

          {syncResult && syncStatus === "success" && (
            <Box
              p={3}
              borderRadius="md"
              bg="green.50"
              borderLeft="4px solid"
              borderColor="green.400"
            >
              <VStack gap={1} align="stretch">
                <Text fontSize="sm" color="green.800" fontWeight="medium">
                  Sync completed
                </Text>
                <Text fontSize="sm" color="green.700">
                  {syncResult.totalEvents} events downloaded,{" "}
                  {syncResult.eventsFound} match this room
                </Text>
                {(syncResult.eventsCreated > 0 ||
                  syncResult.eventsUpdated > 0) && (
                  <Text fontSize="sm" color="green.700">
                    {syncResult.eventsCreated} created,{" "}
                    {syncResult.eventsUpdated} updated
                  </Text>
                )}
              </VStack>
            </Box>
          )}

          {syncMessage && (
            <Box
              p={3}
              borderRadius="md"
              bg={syncStatus === "success" ? "green.50" : "red.50"}
              borderLeft="4px solid"
              borderColor={syncStatus === "success" ? "green.400" : "red.400"}
            >
              <Text
                fontSize="sm"
                color={syncStatus === "success" ? "green.800" : "red.800"}
              >
                {syncMessage}
              </Text>
            </Box>
          )}

          {icsLastSync && (
            <HStack gap={4} fontSize="sm" color="gray.600">
              <HStack>
                <FaCheckCircle color="green" />
                <Text>Last sync: {new Date(icsLastSync).toLocaleString()}</Text>
              </HStack>
              {icsLastEtag && (
                <Badge colorScheme="blue" fontSize="xs">
                  ETag: {icsLastEtag.slice(0, 8)}...
                </Badge>
              )}
            </HStack>
          )}
        </>
      )}
    </VStack>
  );
}
