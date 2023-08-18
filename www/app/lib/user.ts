export async function getCurrentUser(): Promise<any> {
  try {
    const response = await fetch("/api/current-user");

    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }

    const data = await response.json();

    // Ensure the data structure is as expected
    if (data.userinfo && data.access_token_info) {
      return data;
    } else {
      throw new Error("Unexpected data structure");
    }
  } catch (error) {
    console.error("Error fetching the user data:", error);
    throw error; // or you can return an appropriate fallback or error indicator
  }
}
