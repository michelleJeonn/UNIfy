import { type ClientSchema, a, defineData } from '@aws-amplify/backend';

const schema = a.schema({
  UserProfile: a
    .model({
      userId: a.string().required(),
      email: a.string().required(),
      fullName: a.string(),
      school: a.string(),
      gpa: a.float(),
      mentalHealth: a.string(),
      physicalHealth: a.string(),
      severity: a.string(),
      courses: a.string(),
    })
    .authorization((allow) => [allow.owner()]),

  RecommendationHistory: a
    .model({
      userId: a.string().required(),
      timestamp: a.string().required(),
      recommendations: a.string(),
      studentProfile: a.string(),
    })
    .authorization((allow) => [allow.owner()]),
});

export type Schema = ClientSchema<typeof schema>;

export const data = defineData({
  schema,
  authorizationModes: {
    defaultAuthorizationMode: 'userPool',
  },
});
