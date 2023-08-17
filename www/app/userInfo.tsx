"use client";
import { useFiefUserinfo } from "@fief/fief/nextjs/react";

export default function UserInfo() {
  const userinfo = useFiefUserinfo();

  return (
    <>
      {userinfo && (
        <>
          <h1>Logged In</h1>
          <p>{userinfo.email}</p>
        </>
      )}

      {!userinfo && (
        <>
          <h1>Not Logged In</h1>
        </>
      )}
    </>
  );
}
