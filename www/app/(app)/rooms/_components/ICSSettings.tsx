import {
  VStack,
  HStack,
  Field,
  Input,
  Select,
  Checkbox,
  Button,
  Text,
  Alert,
  AlertIcon,
  AlertTitle,
  Badge,
  createListCollection,
  Spinner,
} from "@chakra-ui/react";
import { useState } from "react";
import { FaSync, FaCheckCircle, FaExclamationCircle } from "react-icons/fa";
import useApi from "../../../lib/useApi";

interface ICSSettingsProps {
  roomId?: string;
  roomName?: string;
  icsUrl?: string;
  icsEnabled?: boolean;
  icsFetchInterval?: number;
  icsLastSync?: string;
  icsLastEtag?: string;
  onChange: (settings: Partial<ICSSettingsData>) => void;
  isOwner?: boolean;
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
  roomId,
  roomName,
  icsUrl = "",
  icsEnabled = false,
  icsFetchInterval = 5,
  icsLastSync,
  icsLastEtag,
  onChange,
  isOwner = true,
}: ICSSettingsProps) {
  const [syncStatus, setSyncStatus] = useState<
    "idle" | "syncing" | "success" | "error"
  >("idle");
  const [syncMessage, setSyncMessage] = useState<string>("");
  const [testResult, setTestResult] = useState<string>("");
  const api = useApi();

  const fetchIntervalCollection = createListCollection({
    items: fetchIntervalOptions,
  });

  const handleTestConnection = async () => {
    if (!api || !icsUrl || !roomName) return;

    setSyncStatus("syncing");
    setTestResult("");

    try {
      // First update the room with the ICS URL
      await api.v1RoomsPartialUpdate({
        roomId: roomId || roomName,
        requestBody: {
          ics_url: icsUrl,
          ics_enabled: true,
          ics_fetch_interval: icsFetchInterval,
        },
      });

      // Then trigger a sync
      const result = await api.v1RoomsTriggerIcsSync({ roomName });

      if (result.status === "success") {
        setSyncStatus("success");
        setTestResult(
          `Successfully synced! Found ${result.events_found} events.`,
        );
      } else {
        setSyncStatus("error");
        setTestResult(result.error || "Sync failed");
      }
    } catch (err: any) {
      setSyncStatus("error");
      setTestResult(err.body?.detail || "Failed to test ICS connection");
    }
  };

  const handleManualSync = async () => {
    if (!api || !roomName) return;

    setSyncStatus("syncing");
    setSyncMessage("");

    try {
      const result = await api.v1RoomsTriggerIcsSync({ roomName });

      if (result.status === "success") {
        setSyncStatus("success");
        setSyncMessage(
          `Sync complete! Found ${result.events_found} events, ` +
            `created ${result.events_created}, updated ${result.events_updated}.`,
        );
      } else {
        setSyncStatus("error");
        setSyncMessage(result.error || "Sync failed");
      }
    } catch (err: any) {
      setSyncStatus("error");
      setSyncMessage(err.body?.detail || "Failed to sync calendar");
    }

    // Clear status after 5 seconds
    setTimeout(() => {
      setSyncStatus("idle");
      setSyncMessage("");
    }, 5000);
  };

  if (!isOwner) {
    return null; // ICS settings only visible to room owner
  }

  return (
    <VStack spacing={4} align="stretch" mt={6}>
      <Text fontWeight="semibold" fontSize="lg">
        Calendar Integration (ICS)
      </Text>

      <Field.Root>
        <Checkbox.Root
          checked={icsEnabled}
          onCheckedChange={(e) => onChange({ ics_enabled: e.checked })}
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

          {icsUrl && (
            <HStack spacing={3}>
              <Button
                size="sm"
                variant="outline"
                onClick={handleTestConnection}
                disabled={syncStatus === "syncing"}
                leftIcon={
                  syncStatus === "syncing" ? <Spinner size="sm" /> : undefined
                }
              >
                Test Connection
              </Button>

              {roomName && icsLastSync && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleManualSync}
                  disabled={syncStatus === "syncing"}
                  leftIcon={<FaSync />}
                >
                  Sync Now
                </Button>
              )}
            </HStack>
          )}

          {testResult && (
            <Alert status={syncStatus === "success" ? "success" : "error"}>
              <AlertIcon />
              <Text fontSize="sm">{testResult}</Text>
            </Alert>
          )}

          {syncMessage && (
            <Alert status={syncStatus === "success" ? "success" : "error"}>
              <AlertIcon />
              <Text fontSize="sm">{syncMessage}</Text>
            </Alert>
          )}

          {icsLastSync && (
            <HStack spacing={4} fontSize="sm" color="gray.600">
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
